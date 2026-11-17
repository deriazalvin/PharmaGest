from django.urls import path
from . import views

app_name = "utilisateurs"

urlpatterns = [
    path("", views.liste_utilisateurs, name="liste"),
    path("ajouter/", views.ajouter_utilisateur, name="ajouter"),
    path("<int:pk>/modifier/", views.modifier_utilisateur, name="modifier"),
    path("<int:pk>/desactiver/", views.desactiver_utilisateur, name="desactiver"),
]