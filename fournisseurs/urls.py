from django.urls import path
from . import views

app_name = "fournisseurs"

urlpatterns = [
    path("", views.list_fournisseur, name="liste"),
    path("ajouter/",views.ajouter_fournisseur, name="ajouter_fournisseur"),
    path("<int:pk>/supprimer/",views.supprimer_fournisseur, name="supprimer_fournisseur"),
    path("<int:pk>/modifier/",views.modifier_fournisseur, name="modifier_fournisseur"),
    path("<int:pk>/",views.detail_fournisseur, name="detail_fournisseur"),
]