from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0008_form_visit_details"),
    ]

    operations = [
        migrations.CreateModel(
            name="StudioEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(db_index=True, max_length=64)),
                ("page_path", models.CharField(blank=True, db_index=True, max_length=300)),
                ("props", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "verbose_name": "Studio event",
                "verbose_name_plural": "Studio events",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="studioevent",
            index=models.Index(fields=["name", "created_at"], name="core_studio_name_7f0e1a_idx"),
        ),
    ]
