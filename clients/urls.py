from django.urls import path
from . import views

app_name = "clients"

urlpatterns = [
    path("", views.list_client, name="liste"),
    path("ajouter/",views.ajouter_client, name="ajouter_client"),
    path("<int:pk>/supprimer/",views.supprimer_client, name="supprimer_client"),
    path("<int:pk>/modifier/",views.modifier_client, name="modifier_client"),
    path("<int:pk>/",views.detail_client, name="detail_client"),
]