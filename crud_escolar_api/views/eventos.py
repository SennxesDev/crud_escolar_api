from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import permissions, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from crud_escolar_api.models import Eventos, Maestros, Administradores
from crud_escolar_api.serializers import EventoSerializer, ResponsableSerializer
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

def convertir_hora_12_a_24(hora_str):
    """Convierte formato '12:00 AM/PM' a 'HH:MM:SS'"""
    try:
        if not hora_str:
            return None
        parsed_time = datetime.strptime(hora_str.strip(), "%I:%M %p")
        return parsed_time.strftime("%H:%M:%S")
    except (ValueError, TypeError) as e:
        logger.error(f"Error conversión hora: {str(e)}")
        return None

class EventosAll(generics.ListAPIView):
    """Obtener todos los eventos"""
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = EventoSerializer

    def get_queryset(self):
        return Eventos.objects.order_by("id")

class EventosView(generics.CreateAPIView):
    """Manejo de eventos individuales (GET, POST)"""
    
    def get(self, request, *args, **kwargs):
        """Obtener un evento específico"""
        evento = get_object_or_404(Eventos, id=request.GET.get("id"))
        serializer = EventoSerializer(evento)
        data = serializer.data
        
        # Procesamiento adicional para el frontend
        if isinstance(data['publico_json'], str):
            try:
                data['publico_json'] = json.loads(data['publico_json'])
            except json.JSONDecodeError:
                data['publico_json'] = []
        
        # Formatear horas
        for time_field in ['hora_inicio', 'hora_fin']:
            if data[time_field]:
                data[time_field] = data[time_field][:5]  # "14:00:00" → "14:00"
        
        return Response(data)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """Crear nuevo evento"""
        try:
            # Validación básica
            required_fields = ['name', 'tipo_evento', 'fecha_realizacion', 
                             'hora_inicio', 'hora_fin', 'lugar', 
                             'publico_json', 'cupo_maximo']
            for field in required_fields:
                if field not in request.data:
                    return Response(
                        {"error": f"Campo requerido faltante: {field}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Procesamiento de horas
            hora_inicio = convertir_hora_12_a_24(request.data["hora_inicio"])
            hora_fin = convertir_hora_12_a_24(request.data["hora_fin"])
            
            if not all([hora_inicio, hora_fin]):
                return Response(
                    {"error": "Formato de hora inválido. Usar formato: 'HH:MM AM/PM'"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validación de nombre único
            if Eventos.objects.filter(name=request.data["name"]).exists():
                return Response(
                    {"error": "Ya existe un evento con este nombre"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validación cupo máximo
            try:
                cupo_maximo = int(request.data["cupo_maximo"])
                if cupo_maximo <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                return Response(
                    {"error": "Cupo máximo debe ser un número entero positivo"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Procesamiento público objetivo
            publico_json = request.data["publico_json"]
            if isinstance(publico_json, str):
                try:
                    publico_json = json.loads(publico_json)
                except json.JSONDecodeError:
                    return Response(
                        {"error": "Formato inválido para público objetivo"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            if not isinstance(publico_json, list) or len(publico_json) == 0:
                return Response(
                    {"error": "Se debe seleccionar al menos un público objetivo"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validación programa educativo
            if "Estudiantes" in publico_json and not request.data.get("programa_educativo"):
                return Response(
                    {"error": "Programa educativo es requerido cuando el público incluye estudiantes"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Creación del evento
            evento_data = {
                **request.data,
                "hora_inicio": hora_inicio,
                "hora_fin": hora_fin,
                "publico_json": json.dumps(publico_json),
                "cupo_maximo": cupo_maximo
            }

            serializer = EventoSerializer(data=evento_data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            evento = serializer.save()
            
            return Response(
                {
                    "id": evento.id,
                    "message": "Evento creado exitosamente"
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.error(f"Error al crear evento: {str(e)}")
            return Response(
                {"error": "Error interno al procesar la solicitud"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class EventosViewEdit(generics.UpdateAPIView, generics.DestroyAPIView):
    """Edición y eliminación de eventos"""
    permission_classes = (permissions.IsAuthenticated,)
    queryset = Eventos.objects.all()
    serializer_class = EventoSerializer

    def put(self, request, *args, **kwargs):
        try:
            evento = self.get_object()
            data = request.data.copy()

            # Procesamiento de horas si vienen en el request
            for time_field in ['hora_inicio', 'hora_fin']:
                if time_field in data:
                    hora_convertida = convertir_hora_12_a_24(data[time_field])
                    if not hora_convertida:
                        return Response(
                            {"error": f"Formato inválido para {time_field}"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    data[time_field] = hora_convertida

            # Validación público objetivo
            if 'publico_json' in data:
                if isinstance(data['publico_json'], str):
                    try:
                        data['publico_json'] = json.loads(data['publico_json'])
                    except json.JSONDecodeError:
                        return Response(
                            {"error": "Formato inválido para público objetivo"},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                if "Estudiantes" in data['publico_json'] and not data.get('programa_educativo'):
                    return Response(
                        {"error": "Programa educativo es requerido cuando el público incluye estudiantes"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            serializer = self.get_serializer(evento, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(
                {"message": "Evento actualizado correctamente"},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error al actualizar evento: {str(e)}")
            return Response(
                {"error": "Error interno al actualizar el evento"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, *args, **kwargs):
        try:
            evento = self.get_object()
            evento.delete()
            return Response(
                {"message": "Evento eliminado correctamente"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error al eliminar evento: {str(e)}")
            return Response(
                {"error": "Error interno al eliminar el evento"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ResponsablesAll(APIView):
    """Listado de responsables (maestros + administradores)"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        maestros = Maestros.objects.filter(user__is_active=True).select_related('user')
        admins = Administradores.objects.filter(user__is_active=True).select_related('user')

        responsables = [
            {
                "id": m.user.id,
                "nombre_completo": f"{m.user.first_name} {m.user.last_name}".strip(),
                "tipo": "Maestro"
            } for m in maestros
        ] + [
            {
                "id": a.user.id,
                "nombre_completo": f"{a.user.first_name} {a.user.last_name}".strip(),
                "tipo": "Administrador"
            } for a in admins
        ]

        return Response(responsables, status=status.HTTP_200_OK)