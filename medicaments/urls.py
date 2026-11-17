from django.urls import path
from . import views

app_name = "medicaments"

urlpatterns = [
    path("", views.list_medicament, name="liste_medicaments"),
    path("ajouter/",views.ajouter_medicament, name="ajouter_medicament"),
    path("<int:pk>/supprimer/",views.supprimer_medicament, name="supprimer_medicament"),
    path("<int:pk>/modifier/",views.modifier_medicament, name="modifier_medicament"),
    path("<int:pk>/",views.detail_medicament, name="detail_medicament"),
]