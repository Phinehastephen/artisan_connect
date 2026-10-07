from django.db import migrations

# English starter keywords. Admins add more in Django admin (Service page)
# as the search log shows words customers actually use.
KEYWORDS = {
    "Plumbing": [
        "plumber", "pipe", "leak", "leaking pipe", "water leak", "burst pipe",
        "tap", "faucet", "sink", "toilet", "drain", "blocked drain", "shower",
        "bathroom", "water heater", "water pump", "borehole",
    ],
    "Electrical": [
        "electrician", "electric", "electricity", "wiring", "wire", "socket",
        "switch", "light", "bulb", "no power", "power outage", "short circuit",
        "sparking", "spark", "fuse", "breaker", "inverter", "meter",
    ],
    "Carpentry": [
        "carpenter", "wood", "wooden", "furniture", "door", "cabinet",
        "wardrobe", "cupboard", "table", "chair", "bed frame", "shelf",
        "ceiling", "roof",
    ],
    "Cleaning": [
        "cleaner", "clean", "cleanup", "deep cleaning", "house cleaning",
        "office cleaning", "dust", "dusty", "mop", "sweep", "dirty",
        "post construction cleaning",
    ],
    "Painting": [
        "painter", "paint", "repaint", "wall painting", "emulsion",
        "colour", "color", "peeling paint",
    ],
    "Tailoring": [
        "tailor", "sew", "sewing", "stitch", "clothes", "dress", "suit",
        "trousers", "shirt", "alteration", "adjust clothes", "fashion designer",
    ],
    "Auto Repair": [
        "mechanic", "car", "vehicle", "engine", "brake", "brakes", "tyre",
        "tire", "car battery", "oil change", "gearbox", "car wont start",
    ],
}


def seed(apps, schema_editor):
    Service = apps.get_model("services", "Service")
    ServiceKeyword = apps.get_model("services", "ServiceKeyword")

    for name, keywords in KEYWORDS.items():
        service = Service.objects.filter(name__iexact=name).first()
        if service is None:
            continue
        for keyword in keywords:
            ServiceKeyword.objects.get_or_create(service=service, keyword=keyword)


def unseed(apps, schema_editor):
    ServiceKeyword = apps.get_model("services", "ServiceKeyword")
    for name, keywords in KEYWORDS.items():
        ServiceKeyword.objects.filter(
            service__name__iexact=name, keyword__in=keywords
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0003_servicekeyword"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
