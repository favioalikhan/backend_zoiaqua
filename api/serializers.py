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
    Rol,
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
    email = serializers.EmailField(write_only=True)
    roles = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Rol.objects.all(), required=False
    )
    rol_principal_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Empleado
        fields = "__all__"
        extra_kwargs = {
            "user": {
                "read_only": True
            },  # Evitamos que el usuario sea modificado directamente
        }

    def get_roles_info(self, obj):
        """
        Retorna información detallada de todos los roles del empleado
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

    def create(self, validated_data):
        # Lógica para crear el usuario y asignarlo al empleado
        email = validated_data.pop("email", None)
        roles = validated_data.pop("roles", [])
        rol_principal_id = validated_data.pop("rol_principal_id", None)

        if not email:
            raise serializers.ValidationError({"email": "Este campo es obligatorio."})

        user = CustomUser.objects.create_user(email=email)

        # Asignar el usuario al empleado
        validated_data["user"] = user

        # Crear la instancia de Empleado
        empleado = Empleado.objects.create(**validated_data)

        # Si se proporcionaron roles, asignarlos a través de EmpleadoRol
        for rol in roles:
            EmpleadoRol.objects.create(
                empleado=empleado, rol=rol, es_rol_principal=False
            )

        # Establecer el rol principal si se proporcionó
        if rol_principal_id:
            empleado.establecer_rol_principal(rol_principal_id)

        # Si el empleado requiere acceso al sistema, generar credenciales y enviar email
        if empleado.acceso_sistema:
            empleado.generar_credenciales()

        return empleado

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
        fields = ["email"]

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
            nombre="",  # Campo obligatorio, puedes ajustar según tus necesidades
            apellido_paterno="",
            apellido_materno="",
            dni="",  # Asegúrate de que el campo permita cadenas vacías o ajusta el modelo
            fecha_contratacion=None,  # Si es nullable
            puesto="",
            estado="activo",  # Valor por defecto
            acceso_sistema=False,
            departamento_principal=None,  # Si es nullable
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
