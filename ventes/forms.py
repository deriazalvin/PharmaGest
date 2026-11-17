from django import forms
from django.forms import formset_factory

from clients.models import Client
from medicaments.models import Medicament
from .models import Vente


class VenteForm(forms.Form):
    cle_idempotence = forms.UUIDField(widget=forms.HiddenInput)
    client = forms.ModelChoiceField(
        queryset=Client.objects.filter(status=True),
        required=False,
        empty_label="Client comptoir",
    )
    mode_paiement = forms.ChoiceField(choices=Vente.ModePaiement.choices)


class LigneVenteForm(forms.Form):
    medicament = forms.ModelChoiceField(
        queryset=Medicament.objects.filter(status=True),
        label="Médicament",
    )
    quantite = forms.IntegerField(min_value=1, initial=1, label="Quantité")


LigneVenteFormSet = formset_factory(LigneVenteForm, extra=1, can_delete=True)


class RetourVenteForm(forms.Form):
    quantite = forms.IntegerField(min_value=1)
    motif = forms.CharField(max_length=255)
    remettre_en_stock = forms.BooleanField(required=False)


class AnnulationVenteForm(forms.Form):
    motif = forms.CharField(max_length=255, label="Motif de l'annulation")