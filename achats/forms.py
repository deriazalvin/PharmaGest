from django import forms
from django.db import models
from django.forms import BaseInlineFormSet, inlineformset_factory

from medicaments.models import Medicament
from fournisseurs.models import Fournisseur
from .models import CommandeAchat, LigneAchat


class CommandeAchatForm(forms.ModelForm):
    class Meta:
        model = CommandeAchat
        fields = ("fournisseur",)
        labels = {"fournisseur": "Fournisseur"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fournisseur"].queryset = Fournisseur.objects.filter(status=True)

class LigneAchatForm(forms.ModelForm):
    class Meta:
        model = LigneAchat
        fields = ("medicament", "quantite_commandee", "prix_unitaire")
        labels = {
            "medicament": "Médicament",
            "quantite_commandee": "Quantité commandée",
            "prix_unitaire": "Prix d'achat unitaire",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["medicament"].queryset = Medicament.objects.filter(status=True)


class BaseLigneAchatFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        medicaments = [
            form.cleaned_data["medicament"]
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE")
            and form.cleaned_data.get("medicament")
        ]
        if len(medicaments) != len(set(medicaments)):
            raise forms.ValidationError(
                "Un médicament ne peut apparaître qu'une seule fois dans la commande."
            )


LigneAchatFormSet = inlineformset_factory(
    CommandeAchat,
    LigneAchat,
    form=LigneAchatForm,
    formset=BaseLigneAchatFormSet,
    extra=4,
    can_delete=True,
)


class ReceptionAchatForm(forms.Form):
    def __init__(self, commande, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for ligne in commande.lignes.filter(quantite_recue__lt=models.F("quantite_commandee")):
            restant = ligne.quantite_commandee - ligne.quantite_recue
            self.fields[f"quantite_{ligne.pk}"] = forms.IntegerField(
                label=f"{ligne.medicament} — restant {restant}",
                min_value=0,
                max_value=restant,
                initial=restant,
                required=True,
            )
            self.fields[f"lot_{ligne.pk}"] = forms.CharField(
                label=f"Numéro de lot — {ligne.medicament}",
                max_length=80,
                required=False,
            )
            self.fields[f"peremption_{ligne.pk}"] = forms.DateField(
                label=f"Date de péremption — {ligne.medicament}",
                widget=forms.DateInput(attrs={"type": "date"}),
                required=False,
            )

    def clean(self):
        cleaned_data = super().clean()
        for name, quantity in cleaned_data.items():
            if not name.startswith("quantite_") or not quantity:
                continue
            suffix = name.removeprefix("quantite_")
            if not cleaned_data.get(f"lot_{suffix}"):
                self.add_error(f"lot_{suffix}", "Indiquez le numéro du lot reçu.")
            if not cleaned_data.get(f"peremption_{suffix}"):
                self.add_error(
                    f"peremption_{suffix}", "Indiquez la date de péremption du lot."
                )
            elif cleaned_data[f"peremption_{suffix}"] <= timezone.localdate():
                self.add_error(
                    f"peremption_{suffix}",
                    "Un lot déjà périmé ne peut pas être réceptionné.",
                )
        if not any(
            name.startswith("quantite_") and quantity
            for name, quantity in cleaned_data.items()
        ):
            raise forms.ValidationError("Saisissez au moins une quantité réceptionnée.")
        return cleaned_data

from django.utils import timezone
