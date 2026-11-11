from django.db import migrations, models
import django.db.models.deletion


SERVICE_DATA = {
    "Cake Making": {
        "description": "Custom cakes for birthdays, weddings, and other celebrations.",
        "minimum_price": 15000,
        "maximum_price": 700000,
        "keywords": [
            "cake making", "cake maker", "birthday cake", "wedding cake",
            "custom cake", "cakes",
        ],
    },
    "Makeup artist (MUA)": {
        "description": "Makeup services for bridal, party, photoshoot, and everyday occasions.",
        "minimum_price": 25000,
        "maximum_price": 80000,
        "keywords": [
            "makeup artist", "make-up artist", "mua", "makeup",
            "bridal makeup", "party makeup",
        ],
    },
}

SCOPE_DATA = {
    "Hair Stylist": [
        ("requested_work", "Requested work", [
            ("braiding", "Braiding"),
            ("wig_installation", "Wig installation"),
            ("haircut", "Haircut"),
            ("treatment", "Hair treatment"),
            ("bridal_styling", "Bridal styling"),
        ]),
        ("hair_length", "Hair length", [
            ("short", "Short"),
            ("medium", "Medium"),
            ("long", "Long"),
        ]),
        ("service_location", "Service location", [
            ("customer_location", "At my location"),
            ("salon", "At the salon"),
        ]),
    ],
    "Cake Making": [
        ("occasion", "Occasion", [
            ("wedding", "Wedding"),
            ("birthday", "Birthday"),
            ("other_celebration", "Other celebration"),
        ]),
        ("servings", "Number of servings", [
            ("1_10", "1–10"),
            ("11_25", "11–25"),
            ("26_50", "26–50"),
            ("51_plus", "51+"),
        ]),
        ("tiers", "Number of tiers", [
            ("1", "1 tier"),
            ("2", "2 tiers"),
            ("3_plus", "3+ tiers"),
        ]),
    ],
    "Makeup artist (MUA)": [
        ("occasion", "Occasion", [
            ("bridal", "Bridal"),
            ("party", "Party"),
            ("photoshoot", "Photoshoot"),
            ("everyday", "Everyday"),
        ]),
        ("makeup_coverage", "Makeup style", [
            ("face_only", "Face only"),
            ("face_and_eyes", "Face and eyes"),
            ("full_look", "Full look"),
        ]),
        ("service_location", "Service location", [
            ("customer_location", "At my location"),
            ("artist_location", "At the artist's location"),
        ]),
    ],
    "Plumbing": [
        ("task", "Task", [
            ("leak_repair", "Leak repair"),
            ("blockage", "Blockage"),
            ("fixture_installation", "Fixture installation"),
            ("pipe_work", "Pipe installation or repair"),
            ("inspection", "Inspection"),
        ]),
        ("fixture_area", "Fixture or area", [
            ("tap", "Tap"),
            ("toilet", "Toilet"),
            ("sink", "Sink"),
            ("shower", "Shower"),
            ("pipe", "Pipe"),
            ("other", "Other"),
        ]),
    ],
    "Auto Repair": [
        ("vehicle_make", "Vehicle make", [
            ("toyota", "Toyota"),
            ("mercedes_benz", "Mercedes-Benz"),
            ("bmw", "BMW"),
            ("lexus", "Lexus"),
            ("other", "Other"),
        ]),
        ("job_type", "Type of work", [
            ("diagnosis", "Diagnosis"),
            ("repair", "Repair"),
            ("maintenance", "Maintenance"),
        ]),
        ("vehicle_type", "Vehicle type", [
            ("car", "Car"),
            ("suv", "SUV"),
            ("van", "Van"),
            ("other", "Other"),
        ]),
    ],
}


def seed_scope_catalog(apps, schema_editor):
    Service = apps.get_model("services", "Service")
    ServiceKeyword = apps.get_model("services", "ServiceKeyword")
    ServiceScopeQuestion = apps.get_model("services", "ServiceScopeQuestion")
    ServiceScopeOption = apps.get_model("services", "ServiceScopeOption")

    for service_name, data in SERVICE_DATA.items():
        service = Service.objects.filter(name__iexact=service_name).first()
        if service is None:
            service = Service.objects.create(
                name=service_name,
                description=data["description"],
                minimum_price=data["minimum_price"],
                maximum_price=data["maximum_price"],
                is_active=True,
            )
        elif service_name == "Makeup artist (MUA)":
            service.minimum_price = data["minimum_price"]
            service.maximum_price = data["maximum_price"]
            service.save(update_fields=["minimum_price", "maximum_price"])

        for keyword in data["keywords"]:
            ServiceKeyword.objects.get_or_create(
                service_id=service.id,
                keyword=keyword.lower(),
            )

    for service_name, questions in SCOPE_DATA.items():
        service = Service.objects.filter(name__iexact=service_name).first()
        if service is None:
            continue

        for question_position, (key, label, options) in enumerate(questions):
            question, _created = ServiceScopeQuestion.objects.get_or_create(
                service_id=service.id,
                key=key,
                defaults={
                    "label": label,
                    "position": question_position,
                    "is_active": True,
                },
            )
            for option_position, (value, option_label) in enumerate(options):
                ServiceScopeOption.objects.get_or_create(
                    question_id=question.id,
                    value=value,
                    defaults={
                        "label": option_label,
                        "position": option_position,
                        "is_active": True,
                    },
                )


def unseed_scope_catalog(apps, schema_editor):
    Service = apps.get_model("services", "Service")
    ServiceScopeQuestion = apps.get_model("services", "ServiceScopeQuestion")
    ServiceScopeOption = apps.get_model("services", "ServiceScopeOption")

    for service_name, data in SERVICE_DATA.items():
        service = Service.objects.filter(name__iexact=service_name).first()
        if service is None:
            continue
        for key, label, options in SCOPE_DATA.get(service_name, []):
            question = ServiceScopeQuestion.objects.filter(
                service_id=service.id,
                key=key,
                label=label,
            ).first()
            if question is None:
                continue
            for value, option_label in options:
                ServiceScopeOption.objects.filter(
                    question_id=question.id,
                    value=value,
                    label=option_label,
                ).delete()
            if not ServiceScopeOption.objects.filter(
                question_id=question.id,
            ).exists():
                question.delete()

        if (
            service_name == "Makeup artist (MUA)"
            and service.minimum_price == data["minimum_price"]
            and service.maximum_price == data["maximum_price"]
        ):
            service.maximum_price = 50000
            service.save(update_fields=["maximum_price"])


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0007_hair_stylist_barber_services"),
    ]

    operations = [
        migrations.CreateModel(
            name="ServiceScopeQuestion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("key", models.SlugField(max_length=100)),
                ("label", models.CharField(max_length=150)),
                ("position", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "service",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scope_questions",
                        to="services.service",
                    ),
                ),
            ],
            options={
                "ordering": ["position", "id"],
            },
        ),
        migrations.CreateModel(
            name="ServiceScopeOption",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("value", models.SlugField(max_length=100)),
                ("label", models.CharField(max_length=150)),
                ("position", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="options",
                        to="services.servicescopequestion",
                    ),
                ),
            ],
            options={
                "ordering": ["position", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="servicescopequestion",
            constraint=models.UniqueConstraint(
                fields=("service", "key"),
                name="unique_scope_question_key_per_service",
            ),
        ),
        migrations.AddConstraint(
            model_name="servicescopeoption",
            constraint=models.UniqueConstraint(
                fields=("question", "value"),
                name="unique_scope_option_value_per_question",
            ),
        ),
        migrations.RunPython(seed_scope_catalog, unseed_scope_catalog),
    ]
