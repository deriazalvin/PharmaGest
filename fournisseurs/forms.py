from django import forms
from .models import Fournisseur


class FournisseurForm(forms.ModelForm):
    class Meta:
        model = Fournisseur
        fields = [
            'nom',
            'adresse',
            'telephone',
            'mail',
            'num_fiscal',
            'contact_principal',
            'status',
        ]
        labels = {"mail": "Adresse e-mail", "status": "Fournisseur actif"}
