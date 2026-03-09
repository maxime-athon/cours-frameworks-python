from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Etudiant, Note
from .serializers import EtudiantSerializer, NoteSerializer

class EtudiantViewSet(viewsets.ModelViewSet):
    """
    ViewSet complet : génère automatiquement les 7 routes CRUD
    """
    queryset = Etudiant.objects.filter(actif=True).select_related('filiere').prefetch_related('notes')
    serializer_class = EtudiantSerializer
    permission_classes = [permissions.IsAuthenticated]

    # Filtrage, recherche, tri
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['filiere__code', 'annee', 'actif']
    search_fields = ['nom', 'prenom', 'matricule', 'email']
    ordering_fields = ['nom', 'prenom', 'date_inscription']
    ordering = ['nom', 'prenom']

    # Action personnalisée : GET /api/etudiants/{id}/notes/
    @action(detail=True, methods=['get'], url_path='notes')
    def notes(self, request, pk=None):
        etudiant = self.get_object()
        notes = etudiant.notes.all().order_by('-date')
        serializer = NoteSerializer(notes, many=True)
        return Response(serializer.data)

    # Action personnalisée : POST /api/etudiants/{id}/ajouter-note/
    @action(detail=True, methods=['post'], url_path='ajouter-note')
    def ajouter_note(self, request, pk=None):
        etudiant = self.get_object()
        serializer = NoteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(etudiant=etudiant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Action globale : GET /api/etudiants/statistiques/
    @action(detail=False, methods=['get'])
    def statistiques(self, request):
        from django.db.models import Avg, Count, Min, Max
        stats = Etudiant.objects.filter(actif=True).aggregate(
            total=Count('id'),
            moy=Avg('notes__valeur'),
            note_min=Min('notes__valeur'),
            note_max=Max('notes__valeur'),
        )
        return Response(stats)