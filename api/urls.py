from django.urls import include, path
from rest_framework import routers
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ControlCalidadViewSet,
    CustomTokenObtainPairView,
    DetallePedidoViewSet,
    DistribucionViewSet,
    EmpleadoViewSet,
    InventarioViewSet,
    KPIViewSet,
    MovimientoInventarioViewSet,
    PedidoViewSet,
    ProduccionViewSet,
    ProductoViewSet,
    ReporteViewSet,
    RutaViewSet,
)

router = routers.DefaultRouter()
router.register(r"empleados", EmpleadoViewSet)
router.register(r"productos", ProductoViewSet)
router.register(r"inventarios", InventarioViewSet)
router.register(r"movimientos-inventario", MovimientoInventarioViewSet)
router.register(r"pedidos", PedidoViewSet)
router.register(r"detalles-pedido", DetallePedidoViewSet)
router.register(r"distribuciones", DistribucionViewSet)
router.register(r"rutas", RutaViewSet)
router.register(r"producciones", ProduccionViewSet)
router.register(r"controles-calidad", ControlCalidadViewSet)
router.register(r"kpis", KPIViewSet)
router.register(r"reportes", ReporteViewSet)

urlpatterns = [
    # Rutas de la API
    path("api/", include(router.urls)),
    # Rutas para autenticación con JWT
    path("api/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Rutas para navegación en la API (opcional)
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
]