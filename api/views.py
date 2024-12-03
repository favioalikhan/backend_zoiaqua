from django.db.models import F
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import (
    KPI,
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


# Vista para Producto
class ProductoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para manejar CRUD de productos
    """

    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

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


# Vista para DetallePedido
class DetallePedidoViewSet(viewsets.ModelViewSet):
    queryset = DetallePedido.objects.all()
    serializer_class = DetallePedidoSerializer


# Vista para Distribucion
class DistribucionViewSet(viewsets.ModelViewSet):
    queryset = Distribucion.objects.all()
    serializer_class = DistribucionSerializer


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
