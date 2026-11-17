from django.urls import path
from . import views

app_name = "stock"

urlpatterns = [
    path("", views.liste_stock, name="liste"),
    path("nouveau-lot/", views.ajouter_lot, name="ajouter_lot"),
    path("ajustement/", views.ajuster_stock, name="ajuster"),
    path("<int:pk>/blocage/", views.basculer_blocage_lot, name="bloquer"),
]