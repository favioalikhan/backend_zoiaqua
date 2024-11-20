from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("El Email es obligatorio")
        email = self.normalize_email(email)
        extra_fields.setdefault("tipo_usuario", "empleado")
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("tipo_usuario", "administrador")
        if extra_fields.get("tipo_usuario") != "administrador":
            raise ValueError("El superusuario debe ser de tipo administrador.")
        return self.create_user(email, username, password, **extra_fields)


class CustomUser(AbstractUser):
    tipo_usuario = models.CharField(
        max_length=20,
        choices=[
            ("empleado", "Empleado"),
            ("administrador", "Administrador"),
        ],
        default="empleado",  # Por defecto, el usuario será empleado
    )
    activo = models.BooleanField(default=True)
    eliminado = models.BooleanField(default=False)
    email = models.EmailField(unique=True)

    objects = CustomUserManager()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    # Especifica nombres únicos para relaciones inversas
    groups = models.ManyToManyField(
        "auth.Group",
        related_name="custom_user_set",  # Cambia el nombre por algo único
        blank=True,
        help_text="Los grupos a los que pertenece este usuario.",
        verbose_name="grupos",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="custom_user_set",  # Cambia el nombre por algo único
        blank=True,
        help_text="Permisos específicos del usuario.",
        verbose_name="permisos de usuario",
    )

    def delete(self, *args, **kwargs):
        """Sobrescribe la eliminación para aplicar una baja lógica."""
        self.eliminado = True
        self.save()


class Cliente(models.Model):
    nombre = models.CharField(max_length=100, validators=[MinLengthValidator(1)])
    apellido_paterno = models.CharField(
        max_length=100, validators=[MinLengthValidator(1)]
    )
    apellido_materno = models.CharField(
        max_length=100, validators=[MinLengthValidator(1)]
    )
    telefono = models.CharField(max_length=20, null=True, blank=True)
    direccion = models.TextField()
    ciudad = models.CharField(max_length=100, null=True, blank=True)
    fecha_registro = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["nombre"], name="idx_clientes_nombre")]

    def __str__(self):
        return f"{self.nombre} {self.apellido}"


class Empleado(models.Model):
    ESTADO_CHOICES = [
        ("activo", "Activo"),
        ("inactivo", "Inactivo"),
        ("licencia", "Licencia"),
        ("retirado", "Retirado"),
    ]
    email = models.EmailField(blank=True, max_length=254, null=True, unique=True)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100, validators=[MinLengthValidator(1)])
    apellido = models.CharField(max_length=100, validators=[MinLengthValidator(1)])
    telefono = models.CharField(max_length=20, null=True, blank=True)
    direccion = models.TextField(null=True, blank=True)
    fecha_contratacion = models.DateTimeField()
    puesto = models.CharField(max_length=50, validators=[MinLengthValidator(1)])
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default="activo")
    departamento_principal = models.ForeignKey(
        "Departamento",
        on_delete=models.SET_NULL,
        null=True,
        related_name="empleados_principales",
    )
    roles = models.ManyToManyField("Rol", through="EmpleadoRol")

    class Meta:
        indexes = [models.Index(fields=["email"], name="idx_empleados_email")]

    def save(self, *args, **kwargs):
        if self.user:
            self.email = self.user.email
        super().save(*args, **kwargs)

    def establecer_rol_principal(self, rol_id):
        """
        Establece un rol específico como principal y los demás como secundarios
        """
        try:
            nuevo_rol_principal = self.empleadorol_set.get(rol_id=rol_id)
        except EmpleadoRol.DoesNotExist:
            raise ValueError("El empleado no tiene asignado este rol")

        # Actualizamos todos los roles a no principales
        self.empleadorol_set.update(es_rol_principal=False)

        # Establecemos el nuevo rol principal
        nuevo_rol_principal.es_rol_principal = True
        nuevo_rol_principal.save()

    @property
    def rol_principal(self):
        """Retorna el rol principal del empleado"""
        return self.empleadorol_set.filter(es_rol_principal=True).first()

    def __str__(self):
        return f"{self.nombre} {self.apellido}"


class Rol(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    responsabilidades = models.TextField(null=True, blank=True)
    departamento = models.ForeignKey(
        "Departamento", on_delete=models.CASCADE, related_name="roles"
    )

    def __str__(self):
        return f"{self.nombre} - {self.departamento}"


class EmpleadoRol(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    rol = models.ForeignKey(
        Rol, on_delete=models.CASCADE, related_name="empleado_roles"
    )
    es_rol_principal = models.BooleanField(default=False)
    fecha_asignacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("empleado", "rol")

    def clean(self):
        # Validar que solo exista un rol principal por empleado
        if self.es_rol_principal:
            roles_principales = EmpleadoRol.objects.filter(
                empleado=self.empleado, es_rol_principal=True
            ).exclude(pk=self.pk)
            if roles_principales.exists():
                raise ValidationError("El empleado ya tiene un rol principal asignado.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.empleado} - {self.rol} ({'Principal' if self.es_rol_principal else 'Secundario'})"


class Departamento(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    nombre = models.CharField(max_length=100, validators=[MinLengthValidator(1)])
    descripcion = models.TextField(null=True, blank=True)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    unidad_medida = models.CharField(max_length=50, validators=[MinLengthValidator(1)])
    estado = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["nombre"], name="idx_productos_nombre")]

    def __str__(self):
        return self.nombre


class Inventario(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    numero_lote = models.CharField(max_length=100, null=True, blank=True)
    cantidad_actual = models.IntegerField()
    punto_reorden = models.IntegerField()
    stock_minimo = models.IntegerField()
    fecha_vencimiento = models.DateTimeField(null=True, blank=True)
    control_produccion = models.ForeignKey(
        "ControlProduccionAgua", on_delete=models.SET_NULL, null=True, blank=True
    )
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["producto"], name="idx_inventario_producto"),
            models.Index(fields=["numero_lote"], name="idx_inventario_lote"),
        ]


class MovimientoInventario(models.Model):
    TIPO_MOVIMIENTO_CHOICES = [
        ("entrada", "Entrada"),
        ("salida", "Salida"),
        ("ajuste", "Ajuste"),
    ]

    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE)
    fecha_movimiento = models.DateTimeField()
    tipo_movimiento = models.CharField(max_length=10, choices=TIPO_MOVIMIENTO_CHOICES)
    cantidad = models.IntegerField()
    motivo_movimiento = models.TextField()
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    documento_referencia = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["fecha_movimiento"], name="idx_inventario_fecha")
        ]


class ControlSoploBotellas(models.Model):
    PROVEEDOR_CHOICES = [("Ahise", "Ahise"), ("Damar", "Damar")]

    fecha = models.DateTimeField()
    proveedor_preforma = models.CharField(max_length=10, choices=PROVEEDOR_CHOICES)
    peso_gramos = models.DecimalField(max_digits=10, decimal_places=2)
    volumen_botella_ml = models.IntegerField()
    produccion_buena = models.IntegerField()
    produccion_danada = models.IntegerField()
    produccion_total = models.IntegerField()
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    observaciones = models.TextField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["fecha"], name="idx_control_soplado_fecha")]


class ControlProduccionAgua(models.Model):
    fecha_produccion = models.DateTimeField()
    numero_lote = models.CharField(max_length=100, unique=True)
    fecha_vencimiento = models.DateTimeField()
    botellas_envasadas = models.IntegerField()
    botellas_malogradas = models.IntegerField()
    tapas_malogradas = models.IntegerField()
    etiquetas_malogradas = models.IntegerField()
    total_botella_buenas = models.IntegerField()
    total_paquetes = models.IntegerField()
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    observaciones = models.TextField(null=True, blank=True)
    control_soplado = models.ForeignKey(
        ControlSoploBotellas, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["fecha_produccion"], name="idx_control_produccion_fecha"
            ),
            models.Index(fields=["numero_lote"], name="idx_control_produccion_lote"),
        ]


class InsumoProduccion(models.Model):
    TIPO_INSUMO_CHOICES = [
        ("preforma", "Preforma"),
        ("tapa", "Tapa"),
        ("etiqueta", "Etiqueta"),
    ]

    tipo_insumo = models.CharField(max_length=10, choices=TIPO_INSUMO_CHOICES)
    proveedor = models.CharField(max_length=100)
    stock_actual = models.IntegerField()
    stock_minimo = models.IntegerField()
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_actualizacion = models.DateTimeField(auto_now=True)


class MovimientoInsumo(models.Model):
    TIPO_MOVIMIENTO_CHOICES = [("entrada", "Entrada"), ("salida", "Salida")]

    insumo = models.ForeignKey(InsumoProduccion, on_delete=models.CASCADE)
    fecha_movimiento = models.DateTimeField()
    tipo_movimiento = models.CharField(max_length=10, choices=TIPO_MOVIMIENTO_CHOICES)
    cantidad = models.IntegerField()
    motivo_movimiento = models.TextField()
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)

    class Meta:
        indexes = [
            models.Index(
                fields=["fecha_movimiento"], name="idx_movimientos_insumos_fecha"
            )
        ]


class Pedido(models.Model):
    ESTADO_PEDIDO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("confirmado", "Confirmado"),
        ("cancelado", "Cancelado"),
        ("entregado", "Entregado"),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    fecha_pedido = models.DateTimeField(default=timezone.now)
    estado_pedido = models.CharField(max_length=15, choices=ESTADO_PEDIDO_CHOICES)
    total_pedido = models.DecimalField(max_digits=10, decimal_places=2)
    direccion_envio = models.TextField()
    fecha_entrega_estimada = models.DateTimeField(null=True, blank=True)
    comentarios = models.TextField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["estado_pedido"], name="idx_pedidos_estado"),
            models.Index(fields=["fecha_pedido"], name="idx_pedidos_fecha"),
        ]


class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        indexes = [
            models.Index(fields=["pedido"], name="idx_detalle_pedidos_pedido"),
            models.Index(fields=["producto"], name="idx_detalle_pedidos_producto"),
        ]


class Venta(models.Model):
    ESTADO_VENTA_CHOICES = [
        ("completada", "Completada"),
        ("pendiente", "Pendiente"),
        ("cancelada", "Cancelada"),
    ]

    fecha_venta = models.DateTimeField()
    estado_venta = models.CharField(max_length=15, choices=ESTADO_VENTA_CHOICES)

    class Meta:
        indexes = [
            models.Index(fields=["fecha_venta"], name="idx_ventas_fecha"),
            models.Index(fields=["estado_venta"], name="idx_ventas_estado"),
        ]


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        indexes = [
            models.Index(fields=["venta"], name="idx_detalle_ventas_venta"),
            models.Index(fields=["producto"], name="idx_detalle_ventas_producto"),
        ]


class Produccion(models.Model):
    ESTADO_PRODUCCION_CHOICES = [
        ("programada", "Programada"),
        ("en proceso", "En Proceso"),
        ("completada", "Completada"),
        ("cancelada", "Cancelada"),
    ]

    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField(null=True, blank=True)
    estado_produccion = models.CharField(
        max_length=15, choices=ESTADO_PRODUCCION_CHOICES
    )

    class Meta:
        indexes = [
            models.Index(fields=["estado_produccion"], name="idx_produccion_estado")
        ]


class ControlCalidad(models.Model):
    RESULTADO_CHOICES = [("aprobado", "Aprobado"), ("rechazado", "Rechazado")]

    produccion = models.ForeignKey(Produccion, on_delete=models.CASCADE)
    fecha_inspeccion = models.DateTimeField()
    resultado = models.CharField(max_length=10, choices=RESULTADO_CHOICES)
    observaciones = models.TextField(null=True, blank=True)


class Ruta(models.Model):
    nombre = models.CharField(max_length=100, validators=[MinLengthValidator(1)])
    descripcion = models.TextField(null=True, blank=True)
    tiempo_estimado = models.IntegerField()
    capacidad = models.IntegerField()
    flexibilidad = models.IntegerField()


class AsignacionRuta(models.Model):
    ruta = models.ForeignKey(Ruta, on_delete=models.CASCADE)
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    fecha_asignacion = models.DateTimeField()


class Distribucion(models.Model):
    ESTADO_CHOICES = [
        ("en ruta", "En Ruta"),
        ("entregado", "Entregado"),
        ("retrasado", "Retrasado"),
        ("cancelado", "Cancelado"),
    ]

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    fecha_salida = models.DateTimeField()
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES)
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)

    class Meta:
        indexes = [models.Index(fields=["estado"], name="idx_distribucion_estado")]


class KPI(models.Model):
    nombre = models.CharField(max_length=100, validators=[MinLengthValidator(1)])
    descripcion = models.TextField(null=True, blank=True)
    valor_actual = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    objetivo = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    fecha_actualizacion = models.DateTimeField(auto_now=True)


class Kanban(models.Model):
    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("en proceso", "En Proceso"),
        ("completado", "Completado"),
    ]

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    fecha = models.DateTimeField()
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES)

    class Meta:
        indexes = [models.Index(fields=["estado"], name="idx_kanban_estado")]


class ClusterGeografico(models.Model):
    nombre = models.CharField(max_length=100, validators=[MinLengthValidator(1)])
    descripcion = models.TextField(null=True, blank=True)
    area_cobertura = models.TextField()
    prioridad = models.IntegerField()
    clientes = models.ManyToManyField("Cliente", through="ClienteCluster")

    def __str__(self):
        return self.nombre


class ClienteCluster(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    cluster = models.ForeignKey(ClusterGeografico, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("cliente", "cluster")
        db_table = "clientes_clusters"


class SesionChatbot(models.Model):
    ESTADO_CHOICES = [("activa", "Activa"), ("cerrada", "Cerrada")]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    fecha_inicio = models.DateTimeField(default=timezone.now)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES)

    class Meta:
        indexes = [
            models.Index(fields=["fecha_inicio"], name="idx_sesiones_chatbot_fecha")
        ]
        db_table = "sesiones_chatbot"


class MensajeChatbot(models.Model):
    ENVIADO_POR_CHOICES = [("cliente", "Cliente"), ("chatbot", "Chatbot")]

    sesion_chatbot = models.ForeignKey(SesionChatbot, on_delete=models.CASCADE)
    mensaje = models.TextField()
    fecha_envio = models.DateTimeField(default=timezone.now)
    enviado_por = models.CharField(max_length=10, choices=ENVIADO_POR_CHOICES)

    class Meta:
        db_table = "mensajes_chatbot"


class RegistroSesion(models.Model):
    TIPO_USUARIO_CHOICES = [
        ("empleado", "Empleado"),
    ]

    usuario_id = models.IntegerField()
    tipo_usuario = models.CharField(max_length=10, choices=TIPO_USUARIO_CHOICES)
    fecha_inicio = models.DateTimeField(default=timezone.now)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    ip_direccion = models.CharField(max_length=45, null=True, blank=True)
    dispositivo = models.CharField(max_length=100, null=True, blank=True)
    exitoso = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["fecha_inicio"], name="idx_registro_sesiones_fecha")
        ]
        db_table = "registro_sesiones"


class SeguimientoPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    fecha_evento = models.DateTimeField(default=timezone.now)
    descripcion_evento = models.TextField()
    estado_pedido = models.CharField(max_length=50)

    class Meta:
        indexes = [
            models.Index(fields=["fecha_evento"], name="idx_seguimiento_pedidos_fecha")
        ]
        db_table = "seguimiento_pedidos"


class Reporte(models.Model):
    titulo = models.CharField(max_length=100, validators=[MinLengthValidator(1)])
    descripcion = models.TextField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    tipo_reporte = models.CharField(max_length=50)
    datos_reporte = models.JSONField(
        help_text="Almacena los datos del reporte en formato JSON"
    )

    def __str__(self):
        return self.titulo
