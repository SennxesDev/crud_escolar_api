"""point_experts_api URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from crud_escolar_api.views import bootstrap
from crud_escolar_api.views import users
from crud_escolar_api.views import auth
from crud_escolar_api.views import alumnos
from crud_escolar_api.views import maestros
from crud_escolar_api.views import eventos
from crud_escolar_api.views import responsables
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'eventos', eventos.EventoViewSet, basename='evento')

urlpatterns = [
    # Version
    path('bootstrap/version', bootstrap.VersionView.as_view()),
    
    ## Create Admin
    path('admin/', users.AdminView.as_view()),
    
    # Admin Data
    path('lista-admins/', users.AdminAll.as_view()),
    
    # Edit Admin
    path('admins-edit/', users.AdminsViewEdit.as_view()),
    
    # Create Alumno
    path('alumnos/', alumnos.AlumnosView.as_view()),
    
    # Alumno Data
    path('lista-alumnos/', alumnos.AlumnosAll.as_view()),
    
    # Edit Alumno
    path('alumnos-edit/', alumnos.AlumnosViewEdit.as_view()),
    
    # Create Maestro
    path('maestros/', maestros.MaestrosView.as_view()),
    
    # Maestro Data
    path('lista-maestros/', maestros.MaestrosAll.as_view()),
    
    # Edit Maestro
    path('maestros-edit/', maestros.MaestrosViewEdit.as_view()),
    
    # Login
    path('token/', auth.CustomAuthToken.as_view()),
    
    # Logout
    path('logout/', auth.Logout.as_view()),
    
   #Eventos
    #Create Evento
        path('eventos/', eventos.EventosView.as_view()),
    #Evento Data
        path('lista-eventos/', eventos.EventosAll.as_view()),
    #Edit Evento
        path('eventos-edit/', eventos.EventosViewEdit.as_view()),
        
    # Endpoint para lista de responsables (administradores + maestros)
    path('lista-responsables/', responsables.ResponsablesAll.as_view(), name='lista-responsables'),

    # Incluye las rutas del router para el ViewSet (opcional)
        path('api/', include(router.urls)),

]