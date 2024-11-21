from django.contrib import admin
from django.contrib.admin import ModelAdmin, TabularInline
from django.contrib.auth.admin import UserAdmin
from django.forms import inlineformset_factory

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

    # Incluir el inline para gestionar roles
    inlines = [EmpleadoRolInline]

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

    def save_model(self, request, obj, form, change):
        # Primero, guarda el empleado
        super().save_model(request, obj, form, change)

        # Obtén los roles desde el inline
        rol_formset = inlineformset_factory(
            Empleado, EmpleadoRol, fields=("rol", "es_rol_principal"), extra=0
        )

        # Si necesitas los roles desde el inline, procesa el formset
        if request.POST.get("empleadorol_set-TOTAL_FORMS"):
            formset = rol_formset(request.POST, instance=obj)

            if formset.is_valid():
                formset.save()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.obj = obj  # Pasa el objeto al formulario si es una edición
        return form


# Admin para el modelo EmpleadoRol
class EmpleadoRolAdmin(ModelAdmin):
    model = EmpleadoRol

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


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Cliente)
admin.site.register(Empleado, EmpleadoAdmin)
admin.site.register(Rol, RolAdmin)
admin.site.register(Producto)
admin.site.register(Inventario)
admin.site.register(MovimientoInventario)
admin.site.register(EmpleadoRol, EmpleadoRolAdmin)
admin.site.register(ControlSoploBotellas)
admin.site.register(ControlProduccionAgua)
admin.site.register(InsumoProduccion)
admin.site.register(MovimientoInsumo)
admin.site.register(Pedido)
admin.site.register(DetallePedido)
admin.site.register(Venta)
admin.site.register(DetalleVenta)
admin.site.register(Produccion)
admin.site.register(ControlCalidad)
admin.site.register(Ruta)
admin.site.register(AsignacionRuta)
admin.site.register(Distribucion)
admin.site.register(KPI)
admin.site.register(Kanban)
admin.site.register(ClusterGeografico)
admin.site.register(ClienteCluster)
admin.site.register(SesionChatbot)
admin.site.register(MensajeChatbot)
admin.site.register(Departamento)
admin.site.register(RegistroSesion)
admin.site.register(SeguimientoPedido)
admin.site.register(Reporte)
