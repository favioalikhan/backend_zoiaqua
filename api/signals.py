from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def update_empleado_email(sender, instance, **kwargs):
    if hasattr(instance, "empleado"):
        empleado = instance.empleado
        empleado.email = instance.email
        empleado.save()
