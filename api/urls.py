from django.urls import include, path
from rest_framework import routers
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ControlCalidadViewSet,
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

router = (
    routers.DefaultRouter()
)  # endpoint de la api https://web-production-0b68.up.railway.app/api (Ruta principal)
router.register(
    r"empleados", EmpleadoViewSet
)  # https://web-production-0b68.up.railway.app/api/empleados (Get-List)
router.register(
    r"departamentos", DepartamentoViewSet
)  # https://web-production-0b68.up.railway.app/api/departamentos (Get-List)
router.register(
    r"productos", ProductoViewSet
)  # https://web-production-0b68.up.railway.app/api/productos (Get-List)
router.register(
    r"inventarios", InventarioViewSet
)  # https://web-production-0b68.up.railway.app/api/inventarios (Get-List)
router.register(
    r"movimientos-inventario", MovimientoInventarioViewSet
)  # https://web-production-0b68.up.railway.app/api/movimientos-inventario (Get-List)
router.register(
    r"pedidos", PedidoViewSet
)  # https://web-production-0b68.up.railway.app/api/pedidos (Get-List)
router.register(
    r"detalles-pedido", DetallePedidoViewSet
)  # https://web-production-0b68.up.railway.app/api/detalles-pedido (Get-List)
router.register(
    r"distribuciones", DistribucionViewSet
)  # https://web-production-0b68.up.railway.app/api/distribuciones (Get-List)
router.register(
    r"rutas", RutaViewSet
)  # https://web-production-0b68.up.railway.app/api/rutas (Get-List)
router.register(
    r"producciones", ProduccionViewSet
)  # https://web-production-0b68.up.railway.app/api/producciones (Get-List)
router.register(
    r"controles-calidad", ControlCalidadViewSet
)  # https://web-production-0b68.up.railway.app/api/controles-calidad (Get-List)
router.register(
    r"kpis", KPIViewSet
)  # https://web-production-0b68.up.railway.app/api/kpis (Get-List)
router.register(
    r"reportes", ReporteViewSet
)  # https://web-production-0b68.up.railway.app/api/reportes (Get-List)

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
