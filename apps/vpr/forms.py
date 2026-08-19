from django import forms

from apps.vpr.models import VprTaskCatalogEntry


class VprTaskCatalogEntryForm(forms.ModelForm):
    class Meta:
        model = VprTaskCatalogEntry
        fields = (
            "academic_year",
            "subject",
            "parallel",
            "task_number",
            "task_subnumber",
            "task_code",
            "official_code",
            "max_score",
            "checked_skill",
            "fgos_result",
            "program_section",
            "topic",
            "topic_subsection",
            "difficulty",
            "task_type",
            "short_description",
            "normative_source",
            "is_active",
        )
        widgets = {
            "short_description": forms.Textarea(attrs={"rows": 4}),
        }


class VprTaskCatalogImportForm(forms.Form):
    file = forms.FileField(
        label="Файл справочника",
        help_text="Поддерживаются JSON, Excel (.xlsx) и CSV.",
    )
