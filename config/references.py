from uuid import uuid4

from django.utils import timezone


def make_reference(prefix):
    """Build a short, unique reference before the row is inserted."""
    return f"{prefix}-{timezone.localdate():%Y}-{uuid4().hex[:8].upper()}"
