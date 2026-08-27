from django.core.exceptions import ValidationError
from django.db import transaction


MAX_ARTISAN_SERVICES = 3


@transaction.atomic
def add_service_to_artisan(artisan, service):
    if artisan.services.filter(id=service.id).exists():
        raise ValidationError(
            "This service is already assigned to the artisan."
        )

    if artisan.services.count() >= MAX_ARTISAN_SERVICES:
        raise ValidationError(
            "An artisan can offer a maximum of 3 services."
        )

    if not service.is_active:
        raise ValidationError(
            "This service is currently unavailable."
        )

    artisan.services.add(service)

    return artisan