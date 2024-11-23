from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import (
    KPI,
    ControlCalidad,
    CustomUser,
    DetallePedido,
    Distribucion,
    Empleado,
    EmpleadoRol,
    Inventario,
    MovimientoInventario,
    Pedido,
    Produccion,
    Producto,
    Reporte,
    Ruta,
)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = CustomUser.EMAIL_FIELD

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Agregar campos personalizados al token
        token["username"] = user.username
        token["email"] = user.email

        # Si deseas agregar información del empleado
        try:
            empleado = Empleado.objects.get(user=user)
            token["nombre"] = empleado.nombre
            token["apellido_paterno"] = empleado.apellido_paterno
            token["apellido_materno"] = empleado.apellido_materno
            token["puesto"] = empleado.puesto
            token["acceso_sistema"] = empleado.acceso_sistema
            # Agrega otros campos según sea necesario
        except Empleado.DoesNotExist:
            pass  # Manejo si el usuario no tiene asociado un empleado

        return token

    def validate(self, attrs):
        # Validación inicial y autenticación del usuario
        data = super().validate(attrs)
        user = self.user

        if not user.is_active:
            raise serializers.ValidationError({"detail": "La cuenta está desactivada."})
        try:
            empleado = Empleado.objects.get(user=user)
        except Empleado.DoesNotExist:
            raise serializers.ValidationError(
                {"detail": "No tiene permisos para acceder al sistema."}
            )

        if not empleado.tiene_acceso_sistema():
            raise serializers.ValidationError(
                {"detail": "No tiene permisos para acceder al sistema."}
            )
        data.update(
            {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "nombre": empleado.nombre,
                "apellido_paterno": empleado.apellido_paterno,
                "apellido_materno": empleado.apellido_materno,
                "puesto": empleado.puesto,
                "acceso_sistema": empleado.acceso_sistema,
            }
        )

        return data


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "email"]

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise ValidationError("Un usuario con este correo electrónico ya existe.")
        return value


class EmpleadoSerializer(serializers.ModelSerializer):
    email = serializers.SerializerMethodField(read_only=True)
    roles = serializers.SerializerMethodField()
    rol_principal = serializers.SerializerMethodField()

    class Meta:
        model = Empleado
        fields = "__all__"
        extra_kwargs = {
            "user": {
                "read_only": True
            },  # Evitamos que el usuario sea modificado directamente
        }

    def get_email(self, obj):
        """
        Obtiene el email del usuario relacionado.
        """
        return obj.user.email if obj.user else ""

    def get_roles(self, obj):
        """
        Retorna una lista de roles con detalles (id, nombre, es_principal).
        """
        return [
            {
                "id": rol.rol.id,
                "nombre": rol.rol.nombre,
                "es_principal": rol.es_rol_principal,
            }
            for rol in obj.empleadorol_set.all()
        ]

    def get_rol_principal(self, obj):
        """
        Retorna información del rol principal
        """
        rol_principal = obj.empleadorol_set.filter(es_rol_principal=True).first()
        if rol_principal:
            return {"id": rol_principal.rol.id, "nombre": rol_principal.rol.nombre}
        return None

    def update(self, instance, validated_data):
        # Extraer roles y rol_principal_id de validated_data
        roles = validated_data.pop("roles", None)
        rol_principal_id = validated_data.pop("rol_principal_id", None)

        # Actualizar los campos del empleado
        instance = super().update(instance, validated_data)

        if roles is not None:
            # Actualizar los roles del empleado
            # Eliminar roles existentes
            instance.roles.clear()
            # Asignar nuevos roles
            for rol in roles:
                EmpleadoRol.objects.create(
                    empleado=instance, rol=rol, es_rol_principal=False
                )

        # Establecer el rol principal si se proporcionó
        if rol_principal_id:
            instance.establecer_rol_principal(rol_principal_id)

        return instance

    def destroy(self, instance):
        # Lógica para eliminar el empleado y su usuario asociado
        user = instance.user
        instance.delete()
        if user:
            user.delete()


class EmpleadoRegistroSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True, required=True)

    class Meta:
        model = Empleado
        fields = [
            "email",
            "nombre",
            "apellido_paterno",
            "apellido_materno",
            "dni",
            "telefono",
            "direccion",
            "fecha_contratacion",
            "puesto",
            "estado",
            "departamento_principal",
            "acceso_sistema",
        ]

    def create(self, validated_data):
        email = validated_data.pop("email")

        # Validar si el email ya existe
        if CustomUser.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                {"email": "Este email ya está registrado."}
            )
        # Crear el usuario asociado
        user = CustomUser.objects.create_user(email=email)

        # Crear la instancia inicial de Empleado con campos mínimos
        empleado = Empleado.objects.create(
            user=user,
            nombre=validated_data.get("nombre"),
            apellido_paterno=validated_data.get("apellido_paterno"),
            apellido_materno=validated_data.get("apellido_materno"),
            dni=validated_data.get("dni"),
            telefono=validated_data.get("telefono"),
            direccion=validated_data.get("direccion"),
            fecha_contratacion=validated_data.get("fecha_contratacion"),
            puesto=validated_data.get("puesto"),
            estado=validated_data.get("estado", "activo"),
            departamento_principal=validated_data.get("departamento_principal"),
            acceso_sistema=validated_data.get("acceso_sistema", False),
        )

        return empleado


class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = "__all__"


class InventarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventario
        fields = "__all__"


class MovimientoInventarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimientoInventario
        fields = "__all__"


class DetallePedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetallePedido
        fields = "__all__"


class PedidoSerializer(serializers.ModelSerializer):
    detalles = DetallePedidoSerializer(many=True, read_only=True)

    class Meta:
        model = Pedido
        fields = [
            "id",
            "cliente",
            "fecha_pedido",
            "estado_pedido",
            "total_pedido",
            "direccion_envio",
            "fecha_entrega_estimada",
            "comentarios",
            "detalles",
        ]


class DistribucionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Distribucion
        fields = "__all__"


class RutaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ruta
        fields = "__all__"


class ProduccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Produccion
        fields = "__all__"


class ControlCalidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlCalidad
        fields = "__all__"


class KPISerializer(serializers.ModelSerializer):
    class Meta:
        model = KPI
        fields = "__all__"


class ReporteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reporte
        fields = "__all__"
