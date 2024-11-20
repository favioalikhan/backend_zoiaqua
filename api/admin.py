from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

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


class CustomUserAdmin(BaseUserAdmin):
    model = CustomUser
    list_display = (
        "id",
        "email",
        "username",
        "rol",
        "is_staff",
        "is_active",
    )
    fieldsets = (  # Personaliza la edición del usuario
        (None, {"fields": ("email", "password")}),
        ("Información Personal", {"fields": ("username", "rol")}),
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
                "fields": ("email", "username", "password1", "password2", "rol"),
            },
        ),
    )


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Cliente)
admin.site.register(Empleado)
admin.site.register(Rol)
admin.site.register(Producto)
admin.site.register(Inventario)
admin.site.register(MovimientoInventario)
admin.site.register(EmpleadoRol)
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
