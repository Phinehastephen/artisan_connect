from django.db import migrations
from django.db.models import ProtectedError

# Starting labour-only price ranges (Naira) from 2026 market averages; admins
# adjust them in Django admin as real prices come in.
SERVICES = {
    "Masonry": {
        "description": "Block and brick laying, plastering, screeding, tiling and wall crack repairs.",
        "minimum_price": 10000,
        "maximum_price": 150000,
        "keywords": [
            "mason", "bricklayer", "brick", "block laying", "blockwork",
            "tile", "tiles", "tiler", "tiling", "floor tiles", "wall tiles",
            "wall crack", "crack", "cracked wall", "plaster", "plastering",
            "screeding", "cement", "concrete", "fence", "foundation",
            "interlocking",
        ],
    },
    "Generator Repair": {
        "description": "Generator servicing, fault diagnosis and repairs for petrol and diesel generators.",
        "minimum_price": 15000,
        "maximum_price": 100000,
        "keywords": [
            "generator", "gen", "generator repair", "generator mechanic",
            "generator not starting", "generator servicing", "gen not working",
        ],
    },
    "AC & Refrigeration": {
        "description": "Air conditioner, fridge and freezer installation, gas refill and repairs.",
        "minimum_price": 5000,
        "maximum_price": 80000,
        "keywords": [
            "ac", "air conditioner", "air conditioning", "air condition", "aircondition", "aircon", "split unit",
            "ac gas", "ac not cooling", "fridge", "refrigerator", "freezer",
            "deep freezer", "not cooling", "cold room", "compressor", "hvac",
        ],
    },
}


def seed(apps, schema_editor):
    Service = apps.get_model("services", "Service")
    ServiceKeyword = apps.get_model("services", "ServiceKeyword")

    for name, data in SERVICES.items():
        service, _created = Service.objects.get_or_create(
            name=name,
            defaults={
                "description": data["description"],
                "minimum_price": data["minimum_price"],
                "maximum_price": data["maximum_price"],
            },
        )
        for keyword in data["keywords"]:
            ServiceKeyword.objects.get_or_create(service=service, keyword=keyword)


def unseed(apps, schema_editor):
    Service = apps.get_model("services", "Service")
    ServiceKeyword = apps.get_model("services", "ServiceKeyword")

    for name, data in SERVICES.items():
        ServiceKeyword.objects.filter(
            service__name=name, keyword__in=data["keywords"]
        ).delete()
        # Leave the service if bookings already use it (Booking.service is PROTECT).
        service = Service.objects.filter(name=name).first()
        if service is not None:
            try:
                service.delete()
            except ProtectedError:
                pass


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0005_plumbing_water_keywords"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
