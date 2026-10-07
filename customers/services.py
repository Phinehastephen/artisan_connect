from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from accounts.models import User


USER_FIELDS = ("username", "full_name", "profile_picture")
CUSTOMER_FIELDS = ("default_location",)


@transaction.atomic
def update_customer_profile(customer, fields):
    user = customer.user

    if "username" in fields:
        taken = (
            User.objects.filter(username__iexact=fields["username"])
            .exclude(pk=user.pk)
            .exists()
        )
        if taken:
            raise ValidationError("This username is already taken.")

    user_updates = [name for name in USER_FIELDS if name in fields]
    for name in user_updates:
        setattr(user, name, fields[name])

    customer_updates = [name for name in CUSTOMER_FIELDS if name in fields]
    for name in customer_updates:
        setattr(customer, name, fields[name])

    try:
        if user_updates:
            user.save(update_fields=[*user_updates, "updated_at"])
        if customer_updates:
            customer.save(update_fields=[*customer_updates, "updated_at"])
    except IntegrityError:
        raise ValidationError("This username is already taken.")

    return customer
