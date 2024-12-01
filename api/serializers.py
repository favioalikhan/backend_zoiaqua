from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import (
    KPI,
    ControlCalidad,
    CustomUser,
    Departamento,
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
        fields = ["id", "email"]

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise ValidationError("Un usuario con este correo electrónico ya existe.")
        return value


class DepartamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departamento
        fields = ("id", "nombre")


class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = (
            "id",
            "nombre",
            "responsabilidades",
            "requiere_acceso_sistema",
            "departamento",
        )


class EmpleadoRolSerializer(serializers.ModelSerializer):
    rol = RolSerializer(read_only=True)

    class Meta:
        model = EmpleadoRol
        fields = ("rol", "es_rol_principal")


class EmpleadoSerializer(serializers.ModelSerializer):
    email = serializers.SerializerMethodField(read_only=True)
    departamento_principal = DepartamentoSerializer(read_only=True)
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

    """
    def update(self, instance, validated_data):
        # Extraer roles y rol_principal_id de validated_data
        roles = validated_data.pop("roles", None)
        rol_principal_id = validated_data.pop("rol_principal_id", None)

        # Actualizar los campos del empleado
        instance = super().update(instance, validated_data)

        if roles is not None:
            # Actualizar los roles del empleado
            # Eliminar roles existentes
            # instance.roles.clear()
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
    """


class EmpleadoRegistroSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True, required=True)
    rol_principal = serializers.CharField(
        write_only=True,
        required=True,
        help_text="Nombre o ID del rol principal que se asignará al empleado.",
    )

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
            "fecha_ingreso",
            "fecha_baja",
            "puesto",
            "estado",
            "departamento_principal",
            "acceso_sistema",
            "rol_principal",
        ]

    def validate_rol_principal(self, value):
        """
        Valida que el rol principal exista en la base de datos.
        Permite buscarlo por ID o nombre.
        """
        try:
            if value.isdigit():
                return Rol.objects.get(id=value)
            else:
                return Rol.objects.get(nombre=value)
        except Rol.DoesNotExist:
            raise serializers.ValidationError(
                "El rol principal proporcionado no existe."
            )

    def create(self, validated_data):
        email = validated_data.pop("email")
        rol_principal = validated_data.pop("rol_principal")
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
            fecha_ingreso=validated_data.get("fecha_ingreso"),
            fecha_baja=validated_data.get("fecha_baja"),
            puesto=validated_data.get("puesto"),
            estado=validated_data.get("estado", "activo"),
            departamento_principal=validated_data.get("departamento_principal"),
            acceso_sistema=validated_data.get("acceso_sistema"),
        )

        # Asignar el rol principal al empleado
        EmpleadoRol.objects.create(
            empleado=empleado, rol=rol_principal, es_rol_principal=True
        )

        return empleado


class EmpleadoUpdateSerializer(serializers.ModelSerializer):
    rol_principal = serializers.PrimaryKeyRelatedField(
        queryset=Rol.objects.all(), write_only=True, required=False, allow_null=True
    )
    roles_adicionales = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=Rol.objects.all()),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Empleado
        fields = [
            "nombre",
            "apellido_paterno",
            "apellido_materno",
            "dni",
            "telefono",
            "direccion",
            "fecha_contratacion",
            "fecha_ingreso",
            "fecha_baja",
            "puesto",
            "estado",
            "departamento_principal",
            "acceso_sistema",
            "rol_principal",
            "roles_adicionales",
        ]
        extra_kwargs = {"user": {"read_only": True}}

    def validate(self, attrs):
        # Validate unique DNI
        if "dni" in attrs:
            empleado_actual = self.instance
            if (
                Empleado.objects.exclude(pk=empleado_actual.pk)
                .filter(dni=attrs["dni"])
                .exists()
            ):
                raise serializers.ValidationError(
                    {"dni": "Este DNI ya está registrado para otro empleado."}
                )

        return attrs

    def update(self, instance, validated_data):
        # Extract special fields
        rol_principal = validated_data.pop("rol_principal", None)
        roles_adicionales = validated_data.pop("roles_adicionales", None)

        # Update Empleado fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Manage principal role
        if rol_principal is not None:
            # Deactivate current principal roles
            EmpleadoRol.objects.filter(empleado=instance, es_rol_principal=True).update(
                es_rol_principal=False
            )

            # Create or update principal role if a role is specified
            if rol_principal:
                empleado_rol_principal, _ = EmpleadoRol.objects.get_or_create(
                    empleado=instance,
                    rol=rol_principal,
                    defaults={"es_rol_principal": True},
                )

                if not empleado_rol_principal.es_rol_principal:
                    empleado_rol_principal.es_rol_principal = True
                    empleado_rol_principal.save()

        # Manage additional roles
        if roles_adicionales is not None:
            # Remove existing non-principal roles
            EmpleadoRol.objects.filter(
                empleado=instance, es_rol_principal=False
            ).delete()

            # Add new additional roles
            for rol in roles_adicionales:
                if rol != rol_principal:
                    EmpleadoRol.objects.get_or_create(
                        empleado=instance, rol=rol, defaults={"es_rol_principal": False}
                    )

        return instance


class EmpleadoDeleteSerializer(serializers.ModelSerializer):
    """
    Serializer for deleting an Empleado (Employee) instance.
    Handles the deletion of both the employee and their associated user account.
    """

    class Meta:
        model = Empleado
        fields = []  # No fields needed for deletion

    def delete(self, instance):
        """
        Custom delete method to handle deletion of employee and associated user.

        Args:
            instance (Empleado): The employee instance to be deleted

        Returns:
            None
        """
        try:
            # Get the associated user before deleting the employee
            user = instance.user if hasattr(instance, "user") else None

            # Delete all associated EmpleadoRol instances first
            EmpleadoRol.objects.filter(empleado=instance).delete()

            # Delete the employee instance
            instance.delete()

            # Delete the associated user if it exists
            if user:
                user.delete()

        except Exception as e:
            # Raise a validation error with a descriptive message
            raise serializers.ValidationError(
                {"delete_error": f"Error al eliminar el empleado: {str(e)}"}
            )

    def perform_destroy(self, instance):
        """
        Method to be used with view's destroy action.
        Provides a consistent interface for deletion.
        """
        self.delete(instance)


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
