from django.urls import path
from . import views

app_name = "ventes"

urlpatterns = [
    path("", views.liste_ventes, name="liste"),
    path("nouvelle/", views.nouvelle_vente, name="nouvelle"),
    path("<int:pk>/", views.detail_vente, name="detail"),
    path("<int:pk>/retour/<int:ligne_pk>/", views.enregistrer_retour, name="retour"),
    path("retour/<int:retour_pk>/remboursement/confirmer/", views.confirmer_remboursement, name="confirmer_remboursement"),
    path("<int:pk>/paiement/confirmer/", views.confirmer_paiement, name="confirmer_paiement"),
    path("<int:pk>/annuler/", views.annuler_vente, name="annuler"),
]