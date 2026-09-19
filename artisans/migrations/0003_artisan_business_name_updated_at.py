from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('artisans', '0002_artisan_services'),
    ]

    operations = [
        migrations.AddField(
            model_name='artisan',
            name='business_name_updated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
