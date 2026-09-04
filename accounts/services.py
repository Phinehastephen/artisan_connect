from django.db import transaction

from .models import User
from customers.models import Customer
from artisans.models import Artisan


@transaction.atomic
def register_customer(validated_data):
    phone_number = validated_data.pop("phone_number")
    password = validated_data.pop("password")

    user = User(
        **validated_data,
        role=User.Role.CUSTOMER,
    )

    user.set_password(password)
    user.save()

    Customer.objects.create(
        user=user,
        phone_number=phone_number,
    )

    return user


@transaction.atomic
def register_artisan(validated_data):
    phone_number = validated_data.pop("phone_number")
    password = validated_data.pop("password")

    user = User(
        **validated_data,
        role=User.Role.ARTISAN,
    )

    user.set_password(password)
    user.save()

    Artisan.objects.create(
        user=user,
        phone_number=phone_number,
    )

    return user