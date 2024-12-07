# services/google_maps.py

from datetime import datetime, timedelta, timezone

import googlemaps
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404

from api.models import Distribucion, Empleado, Pedido


def calcular_tiempo_viaje(destino):
    gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
    origen = settings.STORE_ADDRESS
    now = datetime.now()

    directions_result = gmaps.directions(
        origin=origen, destination=destino, mode="driving", departure_time=now
    )

    if not directions_result:
        return None

    duration_seconds = directions_result[0]["legs"][0]["duration"][
        "value"
    ]  # Duración en segundos
    duration = timedelta(seconds=duration_seconds)
    return duration


def crear_distribucion(pedido_id, direccion_cliente, cantidad_paquetes):
    pedido = get_object_or_404(Pedido, id=pedido_id, estado_pedido="confirmado")

    try:
        cantidad = int(cantidad_paquetes)
        if cantidad >= 20:  # Definir umbral para "más paquetes"
            diferencia_departure = timedelta(minutes=15)
        else:
            diferencia_departure = timedelta(minutes=30)

        # Hora del pedido confirmado
        hora_confirmacion = timezone.now()  # Usar timezone-aware
        fecha_salida = hora_confirmacion + diferencia_departure

        # Calcular tiempo de viaje usando Directions API
        tiempo_viaje = calcular_tiempo_viaje(direccion_cliente)
        if not tiempo_viaje:
            return {
                "success": False,
                "error": "No se pudo calcular el tiempo de viaje.",
            }

        fecha_entrega_estimada = fecha_salida + tiempo_viaje

        # Asignar un empleado disponible
        empleado = Empleado.objects.filter(disponible=True).first()
        if not empleado:
            return {
                "success": False,
                "error": "No hay empleados disponibles para la distribución.",
            }

        with transaction.atomic():
            distribucion = Distribucion.objects.create(
                pedido=pedido,
                fecha_salida=fecha_salida,
                fecha_entrega=fecha_entrega_estimada,
                estado="en ruta",
                empleado=empleado,
            )

            empleado.disponible = False  # Marcar como no disponible
            empleado.save()

        return {"success": True, "data": distribucion}

    except ValueError:
        return {
            "success": False,
            "error": "cantidad_paquetes debe ser un número entero.",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
