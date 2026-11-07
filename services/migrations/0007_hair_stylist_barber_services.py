from django.db import migrations
from django.db.models import ProtectedError


SERVICES = {
    "Hair Stylist": {
        "description": "Hair styling, braiding, weaving, natural hair care and related salon services.",
        "minimum_price": 6000,
        "maximum_price": 50000,
        "keywords": [
            "hair stylist", "hair styling", "hairdresser", "hair dressing",
            "hair salon", "braiding", "braids", "braid", "weaving",
            "wig installation", "wig install", "natural hair", "hair treatment",
            "haircut for women", "stylist",
        ],
    },
    "Barber": {
        "description": "Men's haircuts, fades, beard trimming and barbering services.",
        "minimum_price": 3000,
        "maximum_price": 15000,
        "keywords": [
            "barber", "barbershop", "barber shop", "haircut", "fade",
            "low cut", "trim", "beard trim", "beard shaping", "shave",
            "men's haircut", "mens haircut",
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
            service__name=name,
            keyword__in=data["keywords"],
        ).delete()
        service = Service.objects.filter(name=name).first()
        if service is not None:
            try:
                service.delete()
            except ProtectedError:
                pass


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0006_masonry_generator_ac_services"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
