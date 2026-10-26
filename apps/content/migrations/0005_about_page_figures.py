# Replaces the retired About figures.
# "10+ Delivered projects" and "95% client retention" are removed.
# The project count and the country count stay blank, because the website counts those.

from django.db import migrations


def restore_about_figures(apps, schema_editor):
    Page = apps.get_model("content", "Page")
    Page.objects.filter(slug="about").update(
        stat_1_value="6+",
        stat_1_label="Years in technology",
        stat_2_value="",
        stat_2_label="Projects delivered",
        stat_3_value="15",
        stat_3_label="Specialists in our network",
        stat_4_value="",
        stat_4_label="Countries served",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0004_project_updated_at"),
    ]

    operations = [
        migrations.RunPython(restore_about_figures, migrations.RunPython.noop),
    ]
