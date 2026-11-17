from django.urls import path
from . import views

app_name = "categories"

urlpatterns = [
    path("", views.list_categorie, name="liste"),
    path("ajouter/", views.ajouter_categorie, name="ajouter"),
    path("<int:pk>/modifier/", views.modifier_categorie, name="modifier"),
    path("<int:pk>/supprimer/", views.supprimer_categorie, name="supprimer"),
]