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
            token["apellido"] = empleado.apellido
            token["puesto"] = empleado.puesto
            # Agrega otros campos según sea necesario
        except Empleado.DoesNotExist:
            pass  # Manejo si el usuario no tiene asociado un empleado

        return token

    def validate(self, attrs):
        try:
            # Validación inicial y autenticación del usuario
            data = super().validate(attrs)
            user = self.user

            if not user.is_active:
                raise serializers.ValidationError(
                    {"detail": "La cuenta está desactivada."}
                )
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
        except Exception as e:
            # Asegurar que siempre devolvemos una respuesta JSON
            raise serializers.ValidationError({"detail": str(e)})


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "username", "email"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise ValidationError("Un usuario con este correo electrónico ya existe.")
        return value

    def create(self, validated_data):
        user = CustomUser.objects.create_user(**validated_data)
        return user


class EmpleadoSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Empleado
        fields = ["id", "user", "nombre", "apellido", "roles", "puesto"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        user = CustomUser.objects.create_user(**user_data)
        empleado = Empleado.objects.create(user=user, **validated_data)
        return empleado

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user")
        user = instance.user

        instance.nombre = validated_data.get("nombre", instance.nombre)
        instance.apellido = validated_data.get("apellido", instance.apellido)
        instance.puesto = validated_data.get("puesto", instance.puesto)
        instance.save()

        user.username = user_data.get("username", user.username)
        user.email = user_data.get("email", user.email)
        user.save()

        return instance


class EmpleadoRegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirmar_password = serializers.CharField(write_only=True)

    class Meta:
        model = Empleado
        fields = [
            "id",
            "nombre",
            "apellido",
            "email",
            "telefono",
            "direccion",
            "ciudad",
            "codigo_postal",
            "fecha_contratacion",
            "puesto",
            "estado",
            "password",
            "confirmar_password",
        ]

    def validate(self, data):
        if data["password"] != data["confirmar_password"]:
            raise serializers.ValidationError("Las contraseñas no coinciden.")
        return data

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data.pop("confirmar_password")

        email = validated_data.get("email")

        # Crear el CustomUser
        user = CustomUser.objects.create_user(
            email=email,
            username=email,  # Puedes usar el email como username
            password=password,
        )

        # Crear el Empleado asociado
        empleado = Empleado.objects.create(user=user, **validated_data)

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
