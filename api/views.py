from rest_framework import generics, permissions, serializers, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import (
    KPI,
    ControlCalidad,
    DetallePedido,
    Distribucion,
    Empleado,
    Inventario,
    MovimientoInventario,
    Pedido,
    Produccion,
    Producto,
    Reporte,
    Ruta,
)
from .serializers import (
    ControlCalidadSerializer,
    CustomTokenObtainPairSerializer,
    DetallePedidoSerializer,
    DistribucionSerializer,
    EmpleadoRegistroSerializer,
    EmpleadoSerializer,
    InventarioSerializer,
    KPISerializer,
    MovimientoInventarioSerializer,
    PedidoSerializer,
    ProduccionSerializer,
    ProductoSerializer,
    ReporteSerializer,
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


class EmpleadoRegistroView(generics.CreateAPIView):
    queryset = Empleado.objects.all()
    serializer_class = EmpleadoRegistroSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]


# Vista para Producto
class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated]


# Vista para Inventario
class InventarioViewSet(viewsets.ModelViewSet):
    queryset = Inventario.objects.all()
    serializer_class = InventarioSerializer
    permission_classes = [IsAuthenticated]


# Vista para MovimientoInventario
class MovimientoInventarioViewSet(viewsets.ModelViewSet):
    queryset = MovimientoInventario.objects.all()
    serializer_class = MovimientoInventarioSerializer
    permission_classes = [IsAuthenticated]


# Vista para Pedido
class PedidoViewSet(viewsets.ModelViewSet):
    queryset = Pedido.objects.all()
    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated]


# Vista para DetallePedido
class DetallePedidoViewSet(viewsets.ModelViewSet):
    queryset = DetallePedido.objects.all()
    serializer_class = DetallePedidoSerializer
    permission_classes = [IsAuthenticated]


# Vista para Distribucion
class DistribucionViewSet(viewsets.ModelViewSet):
    queryset = Distribucion.objects.all()
    serializer_class = DistribucionSerializer
    permission_classes = [IsAuthenticated]


# Vista para Ruta
class RutaViewSet(viewsets.ModelViewSet):
    queryset = Ruta.objects.all()
    serializer_class = RutaSerializer
    permission_classes = [IsAuthenticated]


# Vista para Produccion
class ProduccionViewSet(viewsets.ModelViewSet):
    queryset = Produccion.objects.all()
    serializer_class = ProduccionSerializer
    permission_classes = [IsAuthenticated]


# Vista para ControlCalidad
class ControlCalidadViewSet(viewsets.ModelViewSet):
    queryset = ControlCalidad.objects.all()
    serializer_class = ControlCalidadSerializer
    permission_classes = [IsAuthenticated]


# Vista para KPI
class KPIViewSet(viewsets.ModelViewSet):
    queryset = KPI.objects.all()
    serializer_class = KPISerializer
    permission_classes = [IsAuthenticated]


# Vista para Reporte
class ReporteViewSet(viewsets.ModelViewSet):
    queryset = Reporte.objects.all()
    serializer_class = ReporteSerializer
    permission_classes = [IsAuthenticated]
