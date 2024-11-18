from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import (
    KPI,
    ControlCalidad,
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
        data = super().validate(attrs)

        # Agregar información adicional a la respuesta
        data.update(
            {
                "username": self.user.username,
                "email": self.user.email,
            }
        )

        # Agregar información del empleado
        try:
            empleado = Empleado.objects.get(user=self.user)
            data.update(
                {
                    "nombre": empleado.nombre,
                    "apellido": empleado.apellido,
                    "puesto": empleado.puesto,
                    # Agrega otros campos según sea necesario
                }
            )
        except Empleado.DoesNotExist:
            pass

        return data


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise ValidationError("Un usuario con este correo electrónico ya existe.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class EmpleadoSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Empleado
        fields = ["id", "user", "nombre", "apellido", "roles", "puesto"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        user = User.objects.create_user(**user_data)
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
