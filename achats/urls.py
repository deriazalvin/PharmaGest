from django.urls import path
from . import views

app_name = "achats"

urlpatterns = [
    path("", views.liste_achats, name="liste"),
    path("creer/", views.creer_achat, name="creer"),
    path("<int:pk>/", views.detail_achat, name="detail"),
    path("<int:pk>/commander/", views.valider_achat, name="valider"),
    path("<int:pk>/receptionner/", views.receptionner_achat, name="receptionner"),
    path("<int:pk>/annuler/", views.annuler_achat, name="annuler"),
]