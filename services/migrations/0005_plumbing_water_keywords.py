from django.db import migrations

# Anything about leaking pipes or water not reaching the taps is Plumbing.
PLUMBING_KEYWORDS = [
    "water", "leakage", "leaky", "dripping", "drip", "pipe leak",
    "water not running", "water not flowing", "water not coming",
    "no water", "low water pressure", "water pressure",
]


def seed(apps, schema_editor):
    Service = apps.get_model("services", "Service")
    ServiceKeyword = apps.get_model("services", "ServiceKeyword")

    service = Service.objects.filter(name__iexact="Plumbing").first()
    if service is None:
        return
    for keyword in PLUMBING_KEYWORDS:
        ServiceKeyword.objects.get_or_create(service=service, keyword=keyword)


def unseed(apps, schema_editor):
    ServiceKeyword = apps.get_model("services", "ServiceKeyword")
    ServiceKeyword.objects.filter(
        service__name__iexact="Plumbing", keyword__in=PLUMBING_KEYWORDS
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0004_seed_service_keywords"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
