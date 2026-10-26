# Clears the retired X account so it is not kept in the database.

from django.db import migrations


def clear_x_url(apps, schema_editor):
    SiteSettings = apps.get_model("content", "SiteSettings")
    SiteSettings.objects.update(x_url="")


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0002_project_results"),
    ]

    operations = [
        migrations.RunPython(clear_x_url, migrations.RunPython.noop),
    ]
