from django.urls import include, path
from rest_framework import routers
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ControlCalidadViewSet,
    ControlProduccionAguaViewSet,
    ControlSoploBotellasViewSet,
    CustomTokenObtainPairView,
    DepartamentoViewSet,
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
    RolesByDepartamentoView,
    RutaViewSet,
    welcome_api_view,
)

router = routers.DefaultRouter()
router.register(r"empleados", EmpleadoViewSet)
router.register(r"departamentos", DepartamentoViewSet)
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
router.register(r"control-soplo-botellas", ControlSoploBotellasViewSet)
router.register(r"control-produccion-agua", ControlProduccionAguaViewSet)

# https://web-production-0b68.up.railway.app/api/reportes asi para todos (Get-List)


urlpatterns = [
    # Rutas de la API
    path("", welcome_api_view, name="welcome"),
    path("api/", include(router.urls)),
    # Rutas para autenticación con JWT
    path("api/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Rutas para navegación en la API (opcional)
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path(
        "api/departamentos/<int:departamento_id>/roles/",
        RolesByDepartamentoView.as_view(),
        name="roles_por_departamento",
    ),
]
