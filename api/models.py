import os

import sendgrid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.crypto import get_random_string
from sendgrid.helpers.mail import Content, Email, Mail, To


class CustomUserManager(BaseUserManager):
    def create_user(self, email, username=None, password=None, **extra_fields):
        if not email:
            raise ValueError("El Email es obligatorio")

        if not username:
            username, first_name, last_name = self.generate_unique_user_data(email)

        email = self.normalize_email(email)
        extra_fields.setdefault("first_name", first_name)
        extra_fields.setdefault("last_name", last_name)

        extra_fields.setdefault("tipo_usuario", "empleado")
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("tipo_usuario", "administrador")

        if extra_fields.get("tipo_usuario") != "administrador":
            raise ValueError("El superusuario debe ser de tipo administrador.")

        # Llama a `create_user` en lugar de `create_superuser`
        return self.create_user(email, username, password, **extra_fields)

    def generate_unique_user_data(self, email):
        """
        Genera un username, first_name y last_name único basado en el email
        """
        # Usa la parte antes del @ del email como base
        base_username = email.split("@")[0]

        # Generar un string aleatorio para asegurar unicidad
        random_string = get_random_string(5)

        # Autogenerar username
        username = f"{base_username}_{random_string}"

        # Autogenerar first_name y last_name basados en el email
        first_name = base_username.capitalize()
        last_name = f"{random_string.capitalize()}"

        # Verificar que el username sea único
        while self.model.objects.filter(username=username).exists():
            random_string = get_random_string(5)
            username = f"{base_username}_{random_string}"
            last_name = f"{random_string.capitalize()}"

        return username, first_name, last_name


class CustomUser(AbstractUser):
    tipo_usuario = models.CharField(
        max_length=20,
        choices=[
            ("empleado", "Empleado"),
            ("administrador", "Administrador"),
        ],
        default="empleado",  # Por defecto, el usuario será empleado
    )
    eliminado = models.BooleanField(default=False)
    email = models.EmailField(unique=True)
    username = models.CharField(
        max_length=150,
        unique=True,
        blank=True,
    )

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
        self.is_active = False
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
        return f"{self.nombre} {self.apellido_paterno} {self.apellido_materno}"


class Empleado(models.Model):
    ESTADO_CHOICES = [
        ("activo", "Activo"),
        ("inactivo", "Inactivo"),
        ("licencia", "Licencia"),
        ("retirado", "Retirado"),
    ]

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100, validators=[MinLengthValidator(1)])
    apellido_paterno = models.CharField(
        max_length=100, validators=[MinLengthValidator(1)]
    )
    apellido_materno = models.CharField(
        max_length=100, validators=[MinLengthValidator(1)]
    )
    dni = models.CharField(
        max_length=20,
        unique=True,  # Asegura que no haya DNIs duplicados
        validators=[
            RegexValidator(
                regex=r"^\d{8}$",  # Validación para DNI peruano (8 dígitos)
                message="El DNI debe contener 8 dígitos numéricos",
                code="invalid_dni",
            )
        ],
        verbose_name="Documento de Identidad",
    )
    telefono = models.CharField(max_length=20, null=True, blank=True)
    direccion = models.TextField(null=True, blank=True)
    fecha_contratacion = models.DateField(
        null=False, help_text="Fecha en que se firma el contrato"
    )
    fecha_ingreso = models.DateField(
        null=True, blank=True, help_text="Fecha real de inicio de trabajo"
    )
    fecha_baja = models.DateField(
        null=True, blank=True, help_text="Fecha de salida de la empresa"
    )
    puesto = models.CharField(max_length=50, validators=[MinLengthValidator(1)])
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default="activo")
    departamento_principal = models.ForeignKey(
        "Departamento",
        on_delete=models.SET_NULL,
        null=True,
        related_name="empleados_principales",
    )
    roles = models.ManyToManyField("Rol", through="EmpleadoRol")
    acceso_sistema = models.BooleanField(
        default=False, verbose_name="Requiere acceso al sistema"
    )

    class Meta:
        indexes = [models.Index(fields=["user"], name="idx_empleados_user")]

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

    def tiene_acceso_sistema(self):
        """
        Determina si el empleado requiere acceso al sistema
        basándose en sus roles o configuración específica
        """
        # Verifica si alguno de sus roles requiere acceso al sistema
        return (
            self.acceso_sistema
            or self.roles.filter(requiere_acceso_sistema=True).exists()
        )

    def generar_credenciales(self):
        if self.tiene_acceso_sistema():
            # Si ya tiene un usuario asociado, generamos solo la contraseña temporal
            if self.user:
                # Regeneramos la contraseña temporal
                password_temporal = self.generar_password_temporal()
                self.user.set_password(password_temporal)
                self.user.is_active = True  # Activamos el usuario si estaba desactivado
                self.user.save()

                credenciales = {
                    "username": self.user.username,
                    "email": self.user.email,
                    "password_temporal": password_temporal,
                    "mensaje": "Credenciales actualizadas para usuario existente",
                }

                self.enviar_credenciales_por_email(credenciales, empleado=self)

                return credenciales

        return None

    def generar_password_temporal(self):
        # Genera una contraseña temporal segura
        return CustomUser.objects.make_random_password(
            length=12,
            allowed_chars="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*",
        )

    def enviar_credenciales_por_email(self, credenciales, empleado=None):
        """
        Envía credenciales de acceso al sistema por correo electrónico usando SendGrid

        :param credenciales: Diccionario con información de credenciales
        :param empleado: Instancia del empleado (opcional, para información adicional)
        :return: Respuesta de SendGrid o None si falla
        """
        try:
            # Inicializar cliente de SendGrid
            sg = sendgrid.SendGridAPIClient(api_key=os.getenv("SENDGRID_API_KEY"))

            # Correo remitente (debe ser un correo verificado)
            from_email = Email("favio_alikhan30@hotmail.com")

            # Correo destinatario
            to_email = To(credenciales["email"])

            # Asunto del correo
            subject = "Credenciales de Acceso al Sistema"

            # Preparar contexto para la plantilla
            context = {
                "nombre_empleado": empleado.nombre if empleado else "Estimado Empleado",
                "username": credenciales["username"],
                "email": credenciales["email"],
                "password_temporal": credenciales["password_temporal"],
            }

            # Renderizar plantilla de correo
            email_template_name = "api/credenciales.html"
            email_body = render_to_string(email_template_name, context)

            # Contenido del correo
            content = Content("text/html", email_body)

            # Crear correo
            mail = Mail(from_email, to_email, subject, content)

            # Enviar correo
            response = sg.send(mail)

            # Imprimir detalles de la respuesta (opcional, para depuración)
            print(f"SendGrid response status code: {response.status_code}")
            print(f"SendGrid response body: {response.body}")
            print(f"SendGrid response headers: {response.headers}")

            return response

        except Exception as e:
            # Loguear el error
            print(f"Error al enviar credenciales por email: {str(e)}")
            return None

    def __str__(self):
        return f"{self.nombre} {self.apellido_paterno} {self.apellido_materno}"


class Rol(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    responsabilidades = models.TextField(null=True, blank=True)
    departamento = models.ForeignKey(
        "Departamento",
        on_delete=models.SET_NULL,
        related_name="roles",
        null=True,
        blank=True,
    )
    requiere_acceso_sistema = models.BooleanField(default=False)

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
        constraints = [
            models.UniqueConstraint(
                fields=["empleado", "rol"], name="unique_empleado_rol"
            )
        ]
        indexes = [
            models.Index(
                fields=["empleado", "es_rol_principal"],
                name="idx_empleado_rol_principal",
            )
        ]

    def clean(self):
        # Validar que solo haya un rol principal por empleado
        if self.es_rol_principal:
            # Buscar si ya existe otro rol principal para este empleado
            principal_exists = (
                EmpleadoRol.objects.filter(
                    empleado=self.empleado, es_rol_principal=True
                )
                .exclude(pk=self.pk)
                .exists()
            )
            if principal_exists:
                raise ValidationError(
                    "El empleado ya tiene un rol principal asignado. Solo puede haber uno."
                )
        super().clean()

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
        return self.titulo
