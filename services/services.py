from django.core.exceptions import ValidationError

from .models import Service


def create_service(
    *,
    name,
    description=None,
    minimum_price,
    maximum_price,
    is_active=True,
):
    service = Service(
        name=name,
        description=description,
        minimum_price=minimum_price,
        maximum_price=maximum_price,
        is_active=is_active,
    )

    service.full_clean()
    service.save()

    return service


def update_service(
    *,
    service,
    name=None,
    description=None,
    minimum_price=None,
    maximum_price=None,
    is_active=None,
):
    if name is not None:
        service.name = name

    if description is not None:
        service.description = description

    if minimum_price is not None:
        service.minimum_price = minimum_price

    if maximum_price is not None:
        service.maximum_price = maximum_price

    if is_active is not None:
        service.is_active = is_active

    service.full_clean()
    service.save()

    return service