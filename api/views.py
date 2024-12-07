from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from api.service import crear_distribucion

from .models import (
    KPI,
    Cliente,
    ControlCalidad,
    ControlProduccionAgua,
    ControlSoploBotellas,
    Departamento,
    DetallePedido,
    Distribucion,
    Empleado,
    Inventario,
    MovimientoInventario,
    Pedido,
    Produccion,
    Producto,
    Reporte,
    Rol,
    Ruta,
)
from .serializers import (
    ClienteSerializer,
    ControlCalidadSerializer,
    ControlProduccionAguaSerializer,
    ControlSoploBotellasSerializer,
    CustomTokenObtainPairSerializer,
    DepartamentoSerializer,
    DetallePedidoSerializer,
    DistribucionSerializer,
    EmpleadoDeleteSerializer,
    EmpleadoRegistroSerializer,
    EmpleadoSerializer,
    EmpleadoUpdateSerializer,
    InventarioSerializer,
    KPISerializer,
    MovimientoInventarioSerializer,
    PedidoSerializer,
    ProduccionSerializer,
    ProductoSerializer,
    ReporteSerializer,
    RolSerializer,
    RutaSerializer,
)


@api_view(["GET"])
def welcome_api_view(request):
    """
    Vista de bienvenida para la API
    Muestra información básica e información de los endpoints disponibles
    """
    return Response(
        {
            "message": "Bienvenido a la API de ZoiaQua",
            "project_name": "ZoiaQua Backend",
            "version": "1.0.0",
            "available_endpoints": [
                {
                    "path": "/api/token/",
                    "method": "POST",
                    "description": "Obtener token de autenticación",
                },
                {
                    "path": "/api/token/refresh/",
                    "method": "POST",
                    "description": "Refrescar token de autenticación",
                },
                # Puedes agregar más endpoints según tu proyecto
            ],
            "documentation": "Consulta la documentación para más detalles",
            "status": "Activo",
        },
        status=status.HTTP_200_OK,
    )


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# Vista para Empleado
class EmpleadoViewSet(viewsets.ModelViewSet):
    queryset = Empleado.objects.all()

    def get_serializer_class(self):
        if self.action == "registro":
            return EmpleadoRegistroSerializer
        elif self.action in ["update", "partial_update"]:
            return EmpleadoUpdateSerializer
        elif self.action == "destroy":
            return EmpleadoDeleteSerializer
        return EmpleadoSerializer

    @action(
        detail=False,
        methods=["post"],
        url_path="registro",
    )
    def registro(self, request):
        """
        Endpoint para registrar un nuevo empleado con su información completa.
        """
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
            empleado = serializer.save()
            return Response(
                EmpleadoSerializer(empleado, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        except serializers.ValidationError as e:
            return Response({"error": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DepartamentoViewSet(viewsets.ModelViewSet):
    queryset = Departamento.objects.all()
    serializer_class = DepartamentoSerializer


class RolesByDepartamentoView(APIView):
    def get(self, request, departamento_id):
        try:
            departamento = Departamento.objects.get(id=departamento_id)
        except Departamento.DoesNotExist:
            return Response(
                {"error": "Departamento no encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Obtener todos los roles asociados al departamento
        roles = Rol.objects.filter(departamento=departamento)

        # Serializar los roles
        serializer = RolSerializer(roles, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


# Vista para cliente
class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer


# Vista para Producto
class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

    @action(detail=False, methods=["get"], url_path="disponibles")
    def disponibles(self, request):
        productos = Producto.objects.filter(estado=True, cantidad_actual__gt=0)
        serializer = self.get_serializer(productos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="check-stock")
    def check_stock(self, request):
        producto_id = request.data.get("producto_id")
        cantidad = request.data.get("cantidad")

        if not producto_id or not cantidad:
            return Response(
                {"error": "producto_id y cantidad son requeridos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        producto = get_object_or_404(Producto, id=producto_id, estado=True)
        inventario = Inventario.objects.filter(producto=producto).first()

        if not inventario or inventario.cantidad_actual < cantidad:
            return Response(
                {"disponible": False, "mensaje": "Stock insuficiente."},
                status=status.HTTP_200_OK,
            )

        total = producto.precio_unitario * float(cantidad)
        return Response(
            {
                "disponible": True,
                "precio_unitario": producto.precio_unitario,
                "total": total,
            },
            status=status.HTTP_200_OK,
        )


# Vista para Inventario
class InventarioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para manejar CRUD de inventarios
    """

    queryset = Inventario.objects.all()
    serializer_class = InventarioSerializer

    @action(detail=False, methods=["get"], url_path="bajo-stock")
    def listar_bajo_stock(self, request):
        """
        Endpoint personalizado para listar inventarios por debajo del stock mínimo.
        """
        inventarios_bajo_stock = Inventario.objects.filter(
            cantidad_actual__lt=F("stock_minimo")
        )
        serializer = self.get_serializer(inventarios_bajo_stock, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["patch"], url_path="actualizar-stock")
    def actualizar_stock(self, request, pk=None):
        """
        Endpoint para actualizar la cantidad actual de un inventario.
        """
        inventario = self.get_object()
        nueva_cantidad = request.data.get("cantidad_actual")
        if nueva_cantidad is None:
            return Response(
                {"error": "Debe proporcionar el campo 'cantidad_actual'"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            inventario.cantidad_actual = int(nueva_cantidad)
            inventario.save()
            return Response(
                {"mensaje": f"Cantidad actualizada a {inventario.cantidad_actual}"},
                status=status.HTTP_200_OK,
            )
        except ValueError:
            return Response(
                {"error": "El valor de 'cantidad_actual' debe ser un número entero"},
                status=status.HTTP_400_BAD_REQUEST,
            )


# Vista para MovimientoInventario
class MovimientoInventarioViewSet(viewsets.ModelViewSet):
    queryset = MovimientoInventario.objects.all()
    serializer_class = MovimientoInventarioSerializer
    permission_classes = [IsAuthenticated]


# Vista para Pedido
class PedidoViewSet(viewsets.ModelViewSet):
    queryset = Pedido.objects.all()
    serializer_class = PedidoSerializer

    @action(detail=False, methods=["post"], url_path="create-temp")
    def create_temp(self, request):
        cliente_id = request.data.get("cliente_id")
        items = request.data.get("items")  # Lista de {producto_id, cantidad}

        if not cliente_id or not items:
            return Response(
                {"error": "cliente_id y items son requeridos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cliente = get_object_or_404(Cliente, id=cliente_id)
        total_pedido = 0
        detalles = []

        for item in items:
            producto = get_object_or_404(Producto, id=item["producto_id"], estado=True)
            inventario = Inventario.objects.filter(producto=producto).first()

            if not inventario or inventario.cantidad_actual < item["cantidad"]:
                return Response(
                    {
                        "error": f"Stock insuficiente para el producto {producto.nombre}."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            subtotal = producto.precio_unitario * float(item["cantidad"])
            total_pedido += subtotal
            detalles.append(
                {
                    "producto": producto.id,
                    "cantidad": item["cantidad"],
                    "precio_unitario": producto.precio_unitario,
                    "subtotal": subtotal,
                }
            )

        pedido = Pedido.objects.create(
            cliente=cliente,
            estado_pedido="pendiente",
            total_pedido=total_pedido,
            direccion_envio=cliente.direccion,
            comentarios=request.data.get("comentarios", ""),
        )

        for detalle in detalles:
            DetallePedido.objects.create(
                pedido=pedido,
                producto_id=detalle["producto"],
                cantidad=detalle["cantidad"],
                precio_unitario=detalle["precio_unitario"],
                subtotal=detalle["subtotal"],
            )

        serializer = self.get_serializer(pedido)
        return Response(
            {"pedido": serializer.data, "total_pedido": total_pedido},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="confirm-payment")
    def confirm_payment(self, request, pk=None):
        # Verificar el token de autorización
        token = request.headers.get("Authorization")
        if token != f"Bearer {settings.CONFIRM_PAYMENT_TOKEN}":
            return Response(
                {"error": "Autenticación inválida."}, status=status.HTTP_403_FORBIDDEN
            )

        pedido = self.get_object()

        if pedido.estado_pedido != "pendiente":
            return Response(
                {"error": "El pedido no está en estado pendiente."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                pedido.estado_pedido = "confirmado"
                pedido.save()

                # Actualizar inventario
                detalles = DetallePedido.objects.select_for_update().filter(
                    pedido=pedido
                )
                for detalle in detalles:
                    inventario = (
                        Inventario.objects.select_for_update()
                        .filter(producto=detalle.producto)
                        .first()
                    )
                    if inventario and inventario.cantidad_actual >= detalle.cantidad:
                        inventario.cantidad_actual -= detalle.cantidad
                        inventario.save()
                    else:
                        raise ValueError(
                            f"Stock insuficiente para {detalle.producto.nombre}"
                        )

                # Crear distribución
                direccion_cliente = pedido.direccion_envio
                cantidad_paquetes = sum([detalle.cantidad for detalle in detalles])

                resultado = crear_distribucion(
                    pedido.id, direccion_cliente, cantidad_paquetes
                )

                if not resultado["success"]:
                    raise ValueError("No se pudo crear la distribución.")

            return Response(
                {"success": True, "mensaje": "Pago confirmado y pedido actualizado."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def create_distribution_manual(
        self, pedido_id, direccion_cliente, cantidad_paquetes
    ):
        # Importar el viewset DistribucionViewSet
        distribucion_viewset = DistribucionViewSet.as_view(
            {"post": "create_distribution"}
        )
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        request = factory.post(
            "/api/distribuciones/create-distribution/",
            {
                "pedido_id": pedido_id,
                "direccion_cliente": direccion_cliente,
                "cantidad_paquetes": cantidad_paquetes,
            },
            format="json",
        )

        response = distribucion_viewset(request)
        if response.status_code == 201:
            return {"success": True, "data": response.data}
        else:
            return {"success": False, "error": response.data}


# Vista para DetallePedido
class DetallePedidoViewSet(viewsets.ModelViewSet):
    queryset = DetallePedido.objects.all()
    serializer_class = DetallePedidoSerializer


# Vista para Distribucion
class DistribucionViewSet(viewsets.ModelViewSet):
    queryset = Distribucion.objects.all()
    serializer_class = DistribucionSerializer

    @action(detail=False, methods=["post"], url_path="create-distribution")
    def create_distribution(self, request):
        pedido_id = request.data.get("pedido_id")
        direccion_cliente = request.data.get("direccion_cliente")
        cantidad_paquetes = request.data.get("cantidad_paquetes")

        if not pedido_id or not direccion_cliente or not cantidad_paquetes:
            return Response(
                {
                    "error": "pedido_id, direccion_cliente y cantidad_paquetes son requeridos."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        resultado = crear_distribucion(pedido_id, direccion_cliente, cantidad_paquetes)

        if resultado["success"]:
            distribucion = resultado["data"]
            serializer = self.get_serializer(distribucion)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {"error": resultado["error"]},
                status=status.HTTP_400_BAD_REQUEST,
            )


# Vista para Ruta
class RutaViewSet(viewsets.ModelViewSet):
    queryset = Ruta.objects.all()
    serializer_class = RutaSerializer


# Vista para Produccion
class ProduccionViewSet(viewsets.ModelViewSet):
    queryset = Produccion.objects.all()
    serializer_class = ProduccionSerializer


# Vista para ControlCalidad
class ControlCalidadViewSet(viewsets.ModelViewSet):
    queryset = ControlCalidad.objects.all()
    serializer_class = ControlCalidadSerializer


class ControlSoploBotellasViewSet(viewsets.ModelViewSet):
    queryset = ControlSoploBotellas.objects.all()
    serializer_class = ControlSoploBotellasSerializer

    @action(detail=False, methods=["get"], url_path="reporte-dano")
    def reporte_dano(self, request):
        """
        Endpoint personalizado para obtener los registros con mayor porcentaje de producción dañada.
        """
        resultados = self.queryset.annotate(
            porcentaje_dano=F("produccion_danada") * 100 / F("produccion_total")
        ).filter(porcentaje_dano__gt=10)  # Ejemplo: producción dañada mayor al 10%

        serializer = self.get_serializer(resultados, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="produccion-por-empleado")
    def produccion_por_empleado(self, request):
        """
        Obtiene un resumen de la producción total por empleado.
        """
        data = self.queryset.values("empleado__nombre").annotate(
            produccion_buena_total=F("produccion_buena"),
            produccion_total=F("produccion_total"),
        )
        return Response(data, status=status.HTTP_200_OK)


class ControlProduccionAguaViewSet(viewsets.ModelViewSet):
    queryset = ControlProduccionAgua.objects.all().order_by("-fecha_produccion")
    serializer_class = ControlProduccionAguaSerializer

    @action(
        detail=False, methods=["get"], url_path="por-empleado/(?P<empleado_id>[^/.]+)"
    )
    def por_empleado(self, request, empleado_id=None):
        """
        Filtra controles de producción realizados por un empleado específico.
        """
        controles = self.queryset.filter(empleado_id=empleado_id)
        serializer = self.get_serializer(controles, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="por-lote/(?P<numero_lote>[^/.]+)")
    def por_lote(self, request, numero_lote=None):
        """
        Filtra controles de producción por número de lote.
        """
        controles = self.queryset.filter(numero_lote=numero_lote)
        serializer = self.get_serializer(controles, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# Vista para KPI
class KPIViewSet(viewsets.ModelViewSet):
    queryset = KPI.objects.all()
    serializer_class = KPISerializer


# Vista para Reporte
class ReporteViewSet(viewsets.ModelViewSet):
    queryset = Reporte.objects.all()
    serializer_class = ReporteSerializer
    serializer_class = ReporteSerializer
