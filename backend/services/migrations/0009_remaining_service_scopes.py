from django.db import migrations


CATALOG_DATA = {
    "Auto Repair": (0, 0),
    "Cake Making": (15000, 70000),
    "Carpentry": (35000, 50000),
    "Cleaning": (15000, 30000),
    "Electrical": (15000, 35000),
    "Makeup artist (MUA)": (25000, 80000),
    "Painting": (21000, 48000),
    "Plumbing": (5000, 10000),
    "Tailoring": (8000, 25000),
}


SCOPE_DATA = {
    "AC & Refrigeration": [
        ("appliance", "Appliance", [
            ("air_conditioner", "Air conditioner"),
            ("refrigerator", "Refrigerator"),
            ("freezer", "Freezer"),
        ]),
        ("requested_work", "Requested work", [
            ("installation", "Installation"),
            ("servicing", "Servicing"),
            ("not_cooling", "Not cooling properly"),
            ("leak_or_noise", "Leak or unusual noise"),
            ("other_fault", "Another fault"),
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
    "Barber": [
        ("requested_work", "Requested work", [
            ("haircut", "Haircut"),
            ("fade", "Fade"),
            ("beard_trim", "Beard trim or shaping"),
            ("shave", "Shave"),
            ("haircut_and_beard", "Haircut and beard"),
        ]),
        ("hair_length", "Current hair length", [
            ("short", "Short"),
            ("medium", "Medium"),
            ("long", "Long"),
        ]),
        ("service_location", "Service location", [
            ("barbershop", "At the barbershop"),
            ("customer_location", "At my location"),
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
    "Carpentry": [
        ("requested_work", "Requested work", [
            ("furniture_repair", "Furniture repair"),
            ("custom_furniture", "Make custom furniture"),
            ("door_or_cabinet", "Door or cabinet work"),
            ("installation", "Furniture installation"),
            ("other_carpentry", "Other carpentry work"),
        ]),
        ("item_type", "Item or area", [
            ("bed", "Bed or bed frame"),
            ("table_or_chair", "Table or chair"),
            ("wardrobe", "Wardrobe"),
            ("door", "Door"),
            ("cabinet", "Cabinet or shelf"),
            ("other_item", "Other"),
        ]),
        ("item_condition", "Current condition", [
            ("new", "New item or installation"),
            ("minor_repair", "Minor repair"),
            ("major_repair", "Major repair"),
        ]),
    ],
    "Cleaning": [
        ("property_type", "Place to clean", [
            ("home", "Home"),
            ("office", "Office"),
            ("shop", "Shop or business"),
            ("other_property", "Other"),
        ]),
        ("cleaning_type", "Type of cleaning", [
            ("regular", "Regular cleaning"),
            ("deep_cleaning", "Deep cleaning"),
            ("move_in_out", "Move-in or move-out cleaning"),
            ("post_construction", "Post-construction cleaning"),
        ]),
        ("property_size", "Approximate size", [
            ("single_room", "Single room"),
            ("few_rooms", "2–3 rooms"),
            ("many_rooms", "4 or more rooms"),
        ]),
    ],
    "Electrical": [
        ("requested_work", "Requested work", [
            ("fault_diagnosis", "Diagnose an electrical fault"),
            ("wiring", "Wiring or rewiring"),
            ("socket_or_switch", "Socket or switch installation"),
            ("lighting", "Lighting installation or repair"),
            ("other_electrical", "Other electrical work"),
        ]),
        ("area_or_item", "Area or item involved", [
            ("lighting", "Light or fixture"),
            ("socket", "Socket or outlet"),
            ("switch", "Switch"),
            ("wiring", "Wiring"),
            ("breaker", "Breaker or fuse box"),
            ("other_item", "Other"),
        ]),
    ],
    "Generator Repair": [
        ("generator_type", "Generator type", [
            ("petrol", "Petrol"),
            ("diesel", "Diesel"),
            ("not_sure", "Not sure"),
        ]),
        ("requested_work", "Requested work", [
            ("fault_diagnosis", "Diagnose a fault"),
            ("not_starting", "Generator will not start"),
            ("not_generating", "Not generating power"),
            ("servicing", "Routine servicing"),
            ("unusual_noise", "Unusual noise or vibration"),
            ("other_generator", "Other generator issue"),
        ]),
    ],
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
    "Masonry": [
        ("requested_work", "Requested work", [
            ("block_laying", "Block or brick laying"),
            ("plastering", "Plastering or screeding"),
            ("tiling", "Floor or wall tiling"),
            ("wall_repair", "Wall crack or surface repair"),
            ("other_masonry", "Other masonry work"),
        ]),
        ("work_area", "Area involved", [
            ("wall", "Wall"),
            ("floor", "Floor"),
            ("bathroom", "Bathroom"),
            ("fence", "Fence"),
            ("other_area", "Other"),
        ]),
        ("work_size", "Approximate work size", [
            ("small_area", "Small area"),
            ("one_room", "About one room"),
            ("multiple_areas", "Multiple areas"),
        ]),
    ],
    "Painting": [
        ("requested_work", "Requested work", [
            ("interior", "Interior painting"),
            ("exterior", "Exterior painting"),
            ("repainting", "Repainting"),
            ("surface_preparation", "Surface preparation"),
            ("other_painting", "Other painting work"),
        ]),
        ("surface_type", "Surface type", [
            ("walls", "Walls"),
            ("ceiling", "Ceiling"),
            ("doors_or_frames", "Doors or frames"),
            ("other_surface", "Other"),
        ]),
        ("work_size", "Approximate work size", [
            ("single_room", "Single room"),
            ("few_rooms", "2–3 rooms"),
            ("many_rooms", "4 or more rooms"),
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
    "Tailoring": [
        ("garment_type", "Garment type", [
            ("dress", "Dress or gown"),
            ("shirt_or_top", "Shirt or top"),
            ("trousers", "Trousers"),
            ("suit", "Suit"),
            ("traditional_wear", "Traditional wear"),
            ("other_garment", "Other garment"),
        ]),
        ("requested_work", "Requested work", [
            ("new_garment", "Make a new garment"),
            ("alteration", "Alter or resize"),
            ("repair", "Repair or restitch"),
            ("adjustment", "Small adjustment"),
        ]),
        ("design_status", "Design or measurements", [
            ("ready", "Design and measurements are ready"),
            ("needs_consultation", "I need help deciding"),
        ]),
    ],
}


def seed_catalog(apps, schema_editor):
    Service = apps.get_model("services", "Service")

    for service_name, (minimum_price, maximum_price) in CATALOG_DATA.items():
        Service.objects.get_or_create(
            name=service_name,
            defaults={
                "minimum_price": minimum_price,
                "maximum_price": maximum_price,
            },
        )


def seed_remaining_scopes(apps, schema_editor):
    Service = apps.get_model("services", "Service")
    Question = apps.get_model("services", "ServiceScopeQuestion")
    Option = apps.get_model("services", "ServiceScopeOption")

    for service_name, questions in SCOPE_DATA.items():
        service = Service.objects.filter(name__iexact=service_name).first()
        if service is None:
            continue

        for question_position, (key, label, options) in enumerate(questions):
            question, _ = Question.objects.get_or_create(
                service_id=service.id,
                key=key,
                defaults={
                    "label": label,
                    "position": question_position,
                    "is_active": True,
                },
            )
            for option_position, (value, option_label) in enumerate(options):
                Option.objects.get_or_create(
                    question_id=question.id,
                    value=value,
                    defaults={
                        "label": option_label,
                        "position": option_position,
                        "is_active": True,
                    },
                )


def unseed_remaining_scopes(apps, schema_editor):
    Service = apps.get_model("services", "Service")
    Question = apps.get_model("services", "ServiceScopeQuestion")

    for service_name, questions in SCOPE_DATA.items():
        service = Service.objects.filter(name__iexact=service_name).first()
        if service is None:
            continue
        for key, label, options in questions:
            question = Question.objects.filter(
                service_id=service.id,
                key=key,
                label=label,
            ).first()
            if question is None:
                continue
            for value, option_label in options:
                question.options.filter(
                    value=value,
                    label=option_label,
                ).delete()
            if not question.options.exists():
                question.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0008_service_scope_questions"),
    ]

    operations = [
        migrations.RunPython(seed_catalog, migrations.RunPython.noop),
        migrations.RunPython(seed_remaining_scopes, unseed_remaining_scopes),
    ]
