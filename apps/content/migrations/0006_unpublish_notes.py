# Every Insights note becomes a draft.
# The title, the summary, and the body are left as they are.

from django.db import migrations


def unpublish_notes(apps, schema_editor):
    Note = apps.get_model("content", "Note")
    Note.objects.update(published=False)


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0005_about_page_figures"),
    ]

    operations = [
        migrations.RunPython(unpublish_notes, migrations.RunPython.noop),
    ]
