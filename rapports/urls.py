from django.urls import path
from . import views

app_name = "rapports"

urlpatterns = [
    path("", views.tableau_de_bord, name="tableau_de_bord"),
    path("ventes.pdf", views.rapport_ventes_pdf, name="ventes_pdf"),
    path("stock.pdf", views.rapport_stock_pdf, name="stock_pdf"),
    path("peremptions.pdf", views.rapport_peremptions_pdf, name="peremptions_pdf"),
    path("achats.pdf", views.rapport_achats_pdf, name="achats_pdf"),
    path("ventes/<int:pk>/recu.pdf", views.recu_vente_pdf, name="recu_vente"),
    path("ventes/<int:pk>/facture.pdf", views.facture_vente_pdf, name="facture_vente"),
    path("achats/<int:pk>/commande.pdf", views.bon_commande_pdf, name="bon_commande"),
    path(
        "achats/<int:pk>/receptions/<int:reception_pk>.pdf",
        views.bon_reception_pdf,
        name="bon_reception",
    ),
]