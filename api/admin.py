from django.contrib.admin import AdminSite, ModelAdmin, TabularInline
from django.contrib.auth.admin import UserAdmin

from .models import (
    KPI,
    AsignacionRuta,
    Cliente,
    ClienteCluster,
    ClusterGeografico,
    ControlCalidad,
    ControlProduccionAgua,
    ControlSoploBotellas,
    CustomUser,
    Departamento,
    DetallePedido,
    DetalleVenta,
    Distribucion,
    Empleado,
    EmpleadoRol,
    InsumoProduccion,
    Inventario,
    Kanban,
    MensajeChatbot,
    MovimientoInsumo,
    MovimientoInventario,
    Pedido,
    Produccion,
    Producto,
    RegistroSesion,
    Reporte,
    Rol,
    Ruta,
    SeguimientoPedido,
    SesionChatbot,
    Venta,
)


class CustomAdminSite(AdminSite):
    site_header = "Panel de Administración"
    site_title = "Administración del Sistema"
    index_title = "Categorías"

    def get_app_list(self, request):
        """
        Sobrescribe la función para personalizar las categorías y modelos.
        """
        app_list = super().get_app_list(request)

        # Definir categorías personalizadas
        categories = {
            "Usuarios y Gestión de Personal": [
                "CustomUser",
                "Empleado",
                "Rol",
                "EmpleadoRol",
                "Departamento",
                "RegistroSesion",
            ],
            "Clientes": [
                "Cliente",
                "ClienteCluster",
                "ClusterGeografico",
                "SeguimientoPedido",
            ],
            "Productos e Inventario": [
                "Producto",
                "Inventario",
                "MovimientoInventario",
                "InsumoProduccion",
                "MovimientoInsumo",
            ],
            "Ventas y Pedidos": [
                "Pedido",
                "DetallePedido",
                "Venta",
                "DetalleVenta",
                "Ruta",
                "AsignacionRuta",
                "Distribucion",
            ],
            "Producción y Control de Calidad": [
                "Produccion",
                "ControlCalidad",
                "ControlProduccionAgua",
                "ControlSoploBotellas",
            ],
            "Gestión de Rendimiento": ["KPI", "Kanban", "Reporte"],
            "Chatbot": ["SesionChatbot", "MensajeChatbot"],
        }

        # Organizar los modelos en categorías
        categorized_apps = []
        for category_name, model_names in categories.items():
            category_models = []
            for app in app_list:
                for model in app["models"]:
                    if model["object_name"] in model_names:
                        category_models.append(model)

            if category_models:
                categorized_apps.append(
                    {"name": category_name, "models": category_models}
                )

        return categorized_apps


custom_admin_site = CustomAdminSite(name="custom_admin")


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = (
        "id",
        "username",
        "email",
        "is_staff",
        "tipo_usuario",
        "is_active",
    )
    list_filter = ("tipo_usuario", "is_staff", "is_active")
    search_fields = ("username", "email")
    ordering = ("username",)
    fieldsets = (  # Personaliza la edición del usuario
        (None, {"fields": ("username", "email", "password")}),
        (
            "Información Personal",
            {"fields": ("first_name", "last_name", "tipo_usuario")},
        ),
        (
            "Permisos",
            {"fields": ("is_staff", "is_active", "groups", "user_permissions")},
        ),
        ("Fechas Importantes", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (  # Personaliza la creación de usuarios
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2"),
            },
        ),
    )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["total_users"] = (
            CustomUser.objects.count()
        )  # Obtén el total de usuarios
        return super().changelist_view(request, extra_context=extra_context)


class EmpleadoRolInline(TabularInline):
    model = EmpleadoRol
    extra = 1  # Para permitir agregar nuevos roles desde la página de administración
    fields = ["rol", "es_rol_principal", "fecha_asignacion"]
    readonly_fields = ["fecha_asignacion"]  # Hacer que la fecha sea de solo lectura
    verbose_name = "Rol del Empleado"
    verbose_name_plural = "Roles del Empleado"


# Admin para el modelo Empleado
class EmpleadoAdmin(ModelAdmin):
    model = Empleado

    list_display = [
        "user",
        "nombre",
        "apellido_paterno",
        "apellido_materno",
        "dni",
        "departamento_principal",
        "estado",
        "acceso_sistema",
    ]
    list_filter = ["estado", "departamento_principal", "acceso_sistema"]
    search_fields = ["user__username", "nombre", "apellido_paterno", "dni"]

    fieldsets = (
        (
            "Información Personal",
            {
                "fields": (
                    "user",
                    "nombre",
                    "apellido_paterno",
                    "apellido_materno",
                    "dni",
                    "telefono",
                    "direccion",
                ),
                "classes": ["tab"],
            },
        ),
        (
            "Información Laboral",
            {
                "fields": (
                    "puesto",
                    "departamento_principal",
                    "estado",
                    "fecha_contratacion",
                    "acceso_sistema",
                ),
                "classes": ["tab"],
            },
        ),
    )

    # Optimización del queryset para mejorar el rendimiento
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("departamento_principal", "user")


# Admin para el modelo EmpleadoRol
class EmpleadoRolAdmin(ModelAdmin):
    model = EmpleadoRol

    inlines = [EmpleadoRolInline]
    list_display = ["empleado", "rol", "es_rol_principal", "fecha_asignacion"]
    list_filter = ["es_rol_principal", "rol"]
    search_fields = ["empleado__nombre", "empleado__dni", "rol__nombre"]

    # Optimización del queryset
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("empleado", "rol")


# Admin para el modelo Rol (si necesitas personalización)
class RolAdmin(ModelAdmin):
    model = Rol

    list_display = ["nombre", "departamento"]
    search_fields = ["nombre", "departamento__nombre"]
    list_filter = ["departamento"]


# Usuarios y Gestión de Personal
custom_admin_site.register(CustomUser, CustomUserAdmin)
custom_admin_site.register(Empleado, EmpleadoAdmin)
custom_admin_site.register(Rol, RolAdmin)
custom_admin_site.register(EmpleadoRol, EmpleadoRolAdmin)
custom_admin_site.register(Departamento)
custom_admin_site.register(RegistroSesion)

# Clientes
custom_admin_site.register(Cliente)
custom_admin_site.register(ClienteCluster)
custom_admin_site.register(ClusterGeografico)
custom_admin_site.register(SeguimientoPedido)

# Productos e Inventario
custom_admin_site.register(Producto)
custom_admin_site.register(Inventario)
custom_admin_site.register(MovimientoInventario)
custom_admin_site.register(InsumoProduccion)
custom_admin_site.register(MovimientoInsumo)

# Ventas y Pedidos
custom_admin_site.register(Pedido)
custom_admin_site.register(DetallePedido)
custom_admin_site.register(Venta)
custom_admin_site.register(DetalleVenta)
custom_admin_site.register(Ruta)
custom_admin_site.register(AsignacionRuta)
custom_admin_site.register(Distribucion)

# Producción y Control de Calidad
custom_admin_site.register(Produccion)
custom_admin_site.register(ControlCalidad)
custom_admin_site.register(ControlProduccionAgua)
custom_admin_site.register(ControlSoploBotellas)

# Gestión de Rendimiento
custom_admin_site.register(KPI)
custom_admin_site.register(Kanban)
custom_admin_site.register(Reporte)

# Chatbot
custom_admin_site.register(SesionChatbot)
custom_admin_site.register(MensajeChatbot)
