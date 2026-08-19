import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("exams", "0001_initial"),
        ("organizations", "0001_initial"),
        ("uploads", "0003_alter_uploadsession_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="uploadsession",
            name="school",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="upload_sessions",
                to="organizations.school",
                verbose_name="Школа",
            ),
        ),
        migrations.AddField(
            model_name="uploadsession",
            name="results_imported",
            field=models.PositiveIntegerField(default=0, verbose_name="Загружено записей"),
        ),
        migrations.AddField(
            model_name="uploadsession",
            name="exams_processed",
            field=models.PositiveIntegerField(default=0, verbose_name="Обработано экзаменов"),
        ),
        migrations.AddField(
            model_name="uploadsession",
            name="reverted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Отменена"),
        ),
        migrations.AddField(
            model_name="uploadsession",
            name="exams",
            field=models.ManyToManyField(blank=True, related_name="upload_sessions", to="exams.exam"),
        ),
    ]
