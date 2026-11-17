from django.core.paginator import Paginator

from utilisateurs.models import JournalAudit


def paginate(request, queryset, per_page=20):
    return Paginator(queryset, per_page).get_page(request.GET.get("page"))


def audit(request, action, obj, details=""):
    JournalAudit.objects.create(
        auteur=request.user if request.user.is_authenticated else None,
        action=action,
        objet=obj._meta.label,
        objet_id=str(obj.pk or ""),
        details=details,
    )
