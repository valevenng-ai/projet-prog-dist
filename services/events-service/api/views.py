from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from rest_framework.response import Response
import requests
from django.conf import settings

from .models import Event, Participant, Registration
from .serializers import (
    EventSerializer,
    EventDetailSerializer,
    ParticipantSerializer,
    RegistrationSerializer,
    RegistrationListSerializer,
)

# Helper qui appelle service-auth
def get_token_info(request):
    token = request.headers.get('Authorization', '').replace('Token ', '')
    try:
        resp = requests.post(
            f"{settings.AUTH_SERVICE_URL}/api/auth/validate-token/",
            json={'token': token},
            timeout=3
        )
        if resp.status_code == 200:
            return resp.json()  # {'valid': True, 'role': 'admin', ...}
    except requests.RequestException:
        pass
    return {'valid': False}

class EventViewSet(viewsets.ModelViewSet):
    """
    CRUD complet pour les événements.

    GET    /events/          → liste tous les événements (avec filtres)
    POST   /events/          → crée un événement
    GET    /events/{id}/     → détail + liste des inscrits
    PUT    /events/{id}/     → mise à jour complète
    PATCH  /events/{id}/     → mise à jour partielle
    DELETE /events/{id}/     → supprime un événement
    GET    /events/{id}/participants/ → liste des participants inscrits
    """

    queryset = Event.objects.all()

    def get_serializer_class(self):
        # Sur le détail d'un événement, on retourne les inscrits
        if self.action == 'retrieve':
            return EventDetailSerializer
        return EventSerializer

    def get_queryset(self):
        queryset = Event.objects.all()

        # Filtre par date
        date = self.request.query_params.get('date')
        if date:
            queryset = queryset.filter(date__date=date)

        # Filtre par statut
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        return queryset

    @action(detail=True, methods=['get'], url_path='participants')
    def participants(self, request, pk=None):
        """GET /events/{id}/participants/ — liste les inscrits d'un événement."""
        event = get_object_or_404(Event, pk=pk)
        registrations = Registration.objects.filter(event=event).select_related('participant')
        serializer = RegistrationListSerializer(registrations, many=True)
        return Response(serializer.data)


class ParticipantViewSet(viewsets.ModelViewSet):
    """
    CRUD complet pour les participants.

    GET    /participants/        → liste tous les participants
    POST   /participants/        → crée un participant
    GET    /participants/{id}/   → détail d'un participant
    PUT    /participants/{id}/   → mise à jour complète
    PATCH  /participants/{id}/   → mise à jour partielle
    DELETE /participants/{id}/   → supprime un participant
    GET    /participants/{id}/events/ → événements auxquels il est inscrit
    """

    queryset = Participant.objects.all()
    serializer_class = ParticipantSerializer

    def get_queryset(self):
        queryset = Participant.objects.all()

        # Recherche par nom ou email
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search) | \
                       queryset.filter(email__icontains=search)

        return queryset

    @action(detail=True, methods=['get'], url_path='events')
    def events(self, request, pk=None):
        """GET /participants/{id}/events/ — liste les événements d'un participant."""
        participant = get_object_or_404(Participant, pk=pk)
        registrations = Registration.objects.filter(participant=participant).select_related('event')
        serializer = RegistrationListSerializer(registrations, many=True)
        return Response(serializer.data)


class RegistrationViewSet(viewsets.ModelViewSet):
    """
    CRUD complet pour les inscriptions.

    GET    /registrations/        → liste toutes les inscriptions
    POST   /registrations/        → inscrit un participant à un événement
    GET    /registrations/{id}/   → détail d'une inscription
    PATCH  /registrations/{id}/   → mise à jour partielle (ex: changer le statut)
    DELETE /registrations/{id}/   → supprime une inscription
    """

    queryset = Registration.objects.select_related('participant', 'event').all()
    serializer_class = RegistrationSerializer

    def get_queryset(self):
        queryset = Registration.objects.select_related('participant', 'event').all()

        # Filtre par événement (ex: ?event=1)
        event_id = self.request.query_params.get('event')
        if event_id:
            queryset = queryset.filter(event__id=event_id)

        # Filtre par participant (ex: ?participant=2)
        participant_id = self.request.query_params.get('participant')
        if participant_id:
            queryset = queryset.filter(participant__id=participant_id)

        return queryset

    def create(self, request, *args, **kwargs):
        """Surcharge pour retourner un message d'erreur clair en cas de double inscription."""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    