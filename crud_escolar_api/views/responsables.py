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

class ResponsablesAll(generics.GenericAPIView):
    """
    Lista todos los administradores y maestros activos como posibles responsables.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        # Obtener administradores y maestros activos
        from crud_escolar_api.models import Administradores, Maestros

        admins = Administradores.objects.filter(user__is_active=True)
        maestros = Maestros.objects.filter(user__is_active=True)

        # Preparar lista unificada
        responsables = []
        for perfil in admins:
            user = perfil.user
            responsables.append({
                'id': perfil.id,
                'nombre_completo': f"{user.first_name} {user.last_name}",
                'rol': 'administrador',
            })
        for perfil in maestros:
            user = perfil.user
            responsables.append({
                'id': perfil.id,
                'nombre_completo': f"{user.first_name} {user.last_name}",
                'rol': 'maestro',
            })

        return Response(responsables, status=status.HTTP_200_OK)