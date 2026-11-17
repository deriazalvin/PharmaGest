from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group


User = get_user_model()


class UtilisateurCreationForm(UserCreationForm):
    groupes = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label="Rôles",
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "groupes")

    def save(self, commit=True):
        utilisateur = super().save(commit=commit)
        if commit:
            utilisateur.groups.set(self.cleaned_data["groupes"])
        return utilisateur


class UtilisateurModificationForm(forms.ModelForm):
    groupes = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label="Rôles",
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "is_active", "groupes")

    def save(self, commit=True):
        utilisateur = super().save(commit=commit)
        if commit:
            utilisateur.groups.set(self.cleaned_data["groupes"])
        return utilisateur