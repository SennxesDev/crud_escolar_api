from django.shortcuts import render
from django.db.models import *
from django.db import transaction
from crud_escolar_api.serializers import *
from crud_escolar_api.models import Eventos  # Importación explícita del modelo
from rest_framework.authentication import BasicAuthentication, SessionAuthentication, TokenAuthentication
from rest_framework.generics import CreateAPIView, DestroyAPIView, UpdateAPIView
from rest_framework import permissions
from rest_framework import generics
from rest_framework import status
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse
from rest_framework import viewsets
from django.shortcuts import get_object_or_404
from django.core import serializers
from django.utils.html import strip_tags
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import Group, User
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as filters
from datetime import datetime
from django.conf import settings
from django.template.loader import render_to_string
import string
import random
import json

def convertir_hora_12_a_24(hora_str):
    """
    Convierte un string en formato '12:00 AM/PM' a formato 'HH:MM:SS'
    """
    try:
        parsed_time = datetime.strptime(hora_str.strip(), "%I:%M %p")
        return parsed_time.strftime("%H:%M:%S")
    except (ValueError, TypeError):
        return None


class EventosAll(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    def get(self, request, *args, **kwargs):
        eventos = Eventos.objects.order_by("id")
        eventos = EventoSerializer(eventos, many=True).data
        if not eventos:
            return Response({}, 400)
        return Response(eventos, status=200)
    
class EventosView(generics.CreateAPIView):
    def get(self, request, *args, **kwargs):
        evento = get_object_or_404(Eventos, id=request.GET.get("id"))
        evento_data = EventoSerializer(evento, many=False).data

        # Convertir publico_json a lista si es string
        raw_publico = evento_data.get("publico_json", "")
    
        if not raw_publico:
            evento_data["publico_json"] = []
        elif isinstance(raw_publico, str):
            try:
                evento_data["publico_json"] = json.loads(raw_publico)
            except json.JSONDecodeError:
                evento_data["publico_json"] = []
        else:
            evento_data["publico_json"] = raw_publico

        # Convertir time a string HH:MM:SS → HH:MM
        if evento_data["hora_inicio"]:
            evento_data["hora_inicio"] = str(evento_data["hora_inicio"])[:5]  # "14:00"

        if evento_data["hora_fin"]:
            evento_data["hora_fin"] = str(evento_data["hora_fin"])[:5]  # "17:00"

        return Response(evento_data, status=200)
    
    # Registrar nuevo evento
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        hora_inicio_str = request.data.get("hora_inicio")
        hora_fin_str = request.data.get("hora_fin")
    
        # Convertimos las horas
        hora_inicio = convertir_hora_12_a_24(hora_inicio_str)
        hora_fin = convertir_hora_12_a_24(hora_fin_str)
    
        if not hora_inicio or not hora_fin:
            return Response({"error": "Formato de hora inválido. Usa hh:mm AM/PM"}, status=400)

        try:
            formato = "%H:%M:%S"
            hora_inicio_time = datetime.strptime(hora_inicio, formato).time()
            hora_fin_time = datetime.strptime(hora_fin, formato).time()
        except ValueError:
            return Response({"error": "Hora inicio/fin debe estar en formato HH:MM:SS"}, status=400)
        
        # Validación de nombre duplicado
        name = request.data.get("name")
        if Eventos.objects.filter(name=name).exists():
            return Response({"message": f"El evento '{name}' ya existe"}, status=400)
    
        # Validación adicional
        cupo_maximo_str = request.data.get("cupo_maximo")
        try:
            cupo_maximo = int(cupo_maximo_str)
        except (ValueError, TypeError):
            return Response({"error": "Cupo máximo debe ser un número válido"}, status=400)
        
        # Parsear publico_json si viene como string
        publico_json = request.data.get("publico_json")
        if isinstance(publico_json, str):
            try:
                publico_json = json.loads(publico_json)
            except json.JSONDecodeError:
                return Response({"error": "Formato de público objetivo inválido"}, status=400)

        # Validar que haya al menos un público objetivo
        if not publico_json or not isinstance(publico_json, list) or len(publico_json) == 0:
            return Response({"error": "Público objetivo es obligatorio"}, status=400)

        # Validar que haya al menos un público objetivo
        if not isinstance(publico_json, list) or len(publico_json) == 0:
            return Response({"error": "Público objetivo es obligatorio"}, status=400)
    
        # Validar programa_educativo si hay estudiantes
        if "Estudiantes" in publico_json and not request.data.get("programa_educativo"):
            return Response({
                "error": "Programa educativo es obligatorio si hay estudiantes"
            }, status=400)
    
        try:
            evento = Eventos.objects.create(
                name=name,
                tipo_evento=request.data.get("tipo_evento"),
                fecha_realizacion=request.data.get("fecha_realizacion"),
                responsable_id=request.data.get("responsable"),  # Usar responsable_id para el ID
                lugar=request.data.get("lugar"),
                hora_inicio=hora_inicio_time,
                hora_fin=hora_fin_time,
                publico_json=publico_json,  # Ya validado como lista
                programa_educativo=request.data.get("programa_educativo"),
                descripcion=request.data.get("descripcion"),
                cupo_maximo=cupo_maximo
            )
            evento.save()

            return Response({"evento_created_id": evento.id }, 201)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
class EventosViewEdit(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    
    def put(self, request, *args, **kwargs):
        evento_id = request.data.get("id")
        evento = get_object_or_404(Eventos, id=evento_id)

        # Parsear publico_json si viene como string
        publico_json = request.data.get("publico_json")
        if isinstance(publico_json, str):
            try:
                publico_json = json.loads(publico_json)
            except json.JSONDecodeError:
                return Response({"error": "Formato de publico_json inválido"}, status=400)

        # Validar si se requiere programa_educativo
        if "Estudiantes" in publico_json and not request.data.get("programa_educativo"):
            return Response({
                "error": "programa_educativo es obligatorio si 'Estudiantes' está seleccionado"
            }, status=400)
        
        # Convertir hora_inicio y hora_fin a objetos time()
        hora_inicio_str = request.data.get("hora_inicio")
        hora_fin_str = request.data.get("hora_fin")

        try:
            formato = "%H:%M:%S"
            hora_inicio = datetime.strptime(hora_inicio_str, formato).time()
            hora_fin = datetime.strptime(hora_fin_str, formato).time()
        except ValueError:
            return Response({"error": "Formato de hora inválido. Usa HH:MM:SS"}, status=400)

        # Actualizar campos
        evento.name = request.data.get("name")
        evento.tipo_evento = request.data.get("tipo_evento")
        evento.fecha_realizacion = request.data.get("fecha_realizacion")

        # Horas ya deben estar en formato HH:MM:SS
        evento.hora_inicio = hora_inicio
        evento.hora_fin = hora_fin

        evento.lugar = request.data.get("lugar")
        evento.publico_json = publico_json  # Ya validado como lista
        evento.programa_educativo = request.data.get("programa_educativo")
        evento.descripcion = request.data.get("descripcion")
        evento.cupo_maximo = int(request.data.get("cupo_maximo"))

        try:
            evento.save()
            return Response({"message": "Evento actualizado correctamente"}, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
    
    def delete(self, request, *args, **kwargs):
        evento = get_object_or_404(Eventos, id=request.GET.get("id"))
        try:
            evento.delete()
            return Response({"details": "Evento eliminado correctamente"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"details": "No se pudo eliminar el evento", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class EventoViewSet(viewsets.ModelViewSet):
    queryset = Eventos.objects.all()
    serializer_class = EventoSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Puedes personalizar el queryset aquí si es necesario
        return Eventos.objects.all().order_by('-fecha_realizacion')