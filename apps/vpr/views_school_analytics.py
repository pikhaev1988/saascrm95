"""Экран и выгрузка «Аналитика школы» ВПР."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from apps.vpr.access import scoped_protocols_qs, user_school
from apps.vpr.comprehensive_analysis import get_protocol_analysis
from apps.vpr.models import VprProtocol
from apps.vpr.school_analysis_cache import get_school_analysis
from apps.vpr.school_analysis.docx_export import generate_school_analysis_docx
from organizations.models import School


def resolve_school_for_request(request) -> School | None:
    role = getattr(request.user, "role", None)
    if role == "school":
        school = user_school(request.user)
        if school is None:
            return None
        return School.objects.filter(pk=school.pk).select_related("district").first() or school
    school_id = request.GET.get("school_id")
    if school_id and str(school_id).isdigit():
        school = School.objects.filter(pk=int(school_id)).select_related("district").first()
        if school is None:
            return None
        if role == "district" and request.user.district_id:
            if school.district_id != request.user.district_id:
                return None
        return school
    protocol = scoped_protocols_qs(request.user).select_related("school", "school__district").first()
    return protocol.school if protocol else None


def parse_selected_year(raw, available_years: list[int]) -> int | None:
    if raw and str(raw).isdigit():
        year = int(raw)
        if year in available_years:
            return year
    return available_years[0] if available_years else None


class VprSchoolAnalyticsView(LoginRequiredMixin, TemplateView):
    """
    Комплексная аналитика ОО по всем протоколам ВПР выбранного года.
    View только получает analysis и передаёт в шаблон.
    """

    template_name = "vpr/school_analytics.html"
    TAB_KEYS = (
        "dashboard",
        "school",
        "subjects",
        "grades",
        "students",
        "deficits",
        "topics-skills",
        "conclusion",
        "recommendations",
        "reports",
    )

    def dispatch(self, request, *args, **kwargs):
        role = getattr(request.user, "role", None)
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if role not in {"school", "district"} and not request.user.is_superuser:
            return redirect("cabinet")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role = getattr(self.request.user, "role", None)
        context["user_role"] = role
        context["cabinet_kind"] = "district" if role == "district" else "school"

        # Район без выбранной школы → свод по району (тот же SAE-дизайн).
        if role == "district" and not (self.request.GET.get("school_id") or "").strip():
            return self._district_overview_context(context)

        school = resolve_school_for_request(self.request)
        if school is None:
            context.update(
                {
                    "school": None,
                    "analysis": None,
                    "selected_year": None,
                    "available_years": [],
                    "available_schools": self._district_schools() if role == "district" else [],
                    "district": getattr(self.request.user, "district", None),
                    "error": "Не удалось определить образовательную организацию.",
                }
            )
            return context

        protocols_qs = scoped_protocols_qs(self.request.user).filter(school=school)
        available_years = list(
            protocols_qs.values_list("academic_year", flat=True).distinct().order_by("-academic_year")
        )
        selected_year = parse_selected_year(self.request.GET.get("year"), available_years)

        active_tab = self.request.GET.get("tab", "dashboard")
        if active_tab not in self.TAB_KEYS:
            active_tab = "dashboard"

        analysis = get_school_analysis(school, selected_year)
        protocols = list(
            protocols_qs.filter(academic_year=selected_year)
            .select_related("upload")
            .order_by("-upload__created_at", "subject", "parallel", "-id")
        )
        selected_protocol = self._resolve_selected_protocol(protocols)
        selected_protocol_analysis = (
            get_protocol_analysis(selected_protocol) if selected_protocol is not None else None
        )
        context.update(
            {
                "school": school,
                "analysis": analysis,
                "selected_year": selected_year,
                "available_years": available_years,
                "available_schools": self._district_schools() if role == "district" else [],
                "district": getattr(self.request.user, "district", None),
                "active_tab": active_tab,
                "protocols": protocols,
                "selected_protocol": selected_protocol,
                "protocol_analysis": selected_protocol_analysis,
                "subject_filter": self.request.GET.get("subject", "").strip(),
                "parallel_filter": self.request.GET.get("parallel", "").strip(),
                "student_query": self.request.GET.get("student_q", "").strip(),
                "error": None,
            }
        )
        return context

    def _district_schools(self):
        if not getattr(self.request.user, "district_id", None):
            return []
        return list(
            School.objects.filter(district_id=self.request.user.district_id)
            .only("id", "name", "code")
            .order_by("name")
        )

    def _district_overview_context(self, context):
        from users.report_ui.district_vpr_dashboard import build_district_vpr_dashboard_ui

        district = getattr(self.request.user, "district", None)
        protocols_qs = scoped_protocols_qs(self.request.user).select_related("school", "upload")
        available_years = list(
            protocols_qs.values_list("academic_year", flat=True).distinct().order_by("-academic_year")
        )
        selected_year = parse_selected_year(self.request.GET.get("year"), available_years)
        year_protocols = protocols_qs
        if selected_year:
            year_protocols = protocols_qs.filter(academic_year=selected_year)
        context.update(
            {
                "school": None,
                "analysis": None,
                "error": None,
                "district_overview": True,
                "district": district,
                "role_title": getattr(district, "name", None) or "Район",
                "available_years": available_years,
                "district_available_years": available_years,
                "selected_year": selected_year,
                "district_selected_year": selected_year,
                "selected_exam_type": "vpr",
                "district_vpr_ui": build_district_vpr_dashboard_ui(
                    protocols=list(year_protocols.order_by("school__name", "subject", "parallel")),
                    selected_year=selected_year,
                    district=district,
                ),
            }
        )
        self.template_name = "vpr/district_analytics.html"
        return context

    def _resolve_selected_protocol(self, protocols: list[VprProtocol]) -> VprProtocol | None:
        if not protocols:
            return None
        protocol_id_raw = self.request.GET.get("protocol_id")
        if protocol_id_raw and protocol_id_raw.isdigit():
            protocol_id = int(protocol_id_raw)
            for protocol in protocols:
                if protocol.id == protocol_id:
                    return protocol
        return protocols[0]


class VprSchoolAnalyticsDocxView(LoginRequiredMixin, View):
    """Скачать аналитику школы ВПР в формате Word."""

    def dispatch(self, request, *args, **kwargs):
        role = getattr(request.user, "role", None)
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if role not in {"school", "district"} and not request.user.is_superuser:
            return redirect("cabinet")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        school = resolve_school_for_request(request)
        if school is None:
            raise Http404("Школа не найдена.")

        protocols_qs = scoped_protocols_qs(request.user).filter(school=school)
        available_years = list(
            protocols_qs.values_list("academic_year", flat=True).distinct().order_by("-academic_year")
        )
        selected_year = parse_selected_year(request.GET.get("year"), available_years)
        analysis = get_school_analysis(school, selected_year)
        protocol_task_tables = []
        year_protocols = list(
            protocols_qs.filter(academic_year=selected_year)
            .select_related("upload")
            .order_by("subject", "parallel", "-id")
        )
        for protocol in year_protocols:
            protocol_analysis = get_protocol_analysis(protocol)
            rows = []
            for row in getattr(protocol_analysis, "task_rows", None) or []:
                correct = int(row.get("correct_count") or row.get("full_count") or 0)
                total = int(row.get("answers_count") or row.get("total") or 0)
                incorrect = int(
                    row.get("minus")
                    if row.get("minus") is not None
                    else row.get("incorrect_count")
                    if row.get("incorrect_count") is not None
                    else max(0, total - correct)
                )
                rows.append(
                    {
                        "task_code": row.get("task_code"),
                        "topic": row.get("topic") or "",
                        "skill": row.get("checked_skill") or "",
                        "completion_percent": row.get("success_rate")
                        if row.get("success_rate") is not None
                        else row.get("completion_percent"),
                        "correct_count": correct,
                        "incorrect_count": incorrect,
                        "partial_count": row.get("partial_count") or 0,
                        "answers_count": total,
                    }
                )
            if rows:
                protocol_task_tables.append(
                    {
                        "title": f"{protocol.subject} · {protocol.parallel} кл.",
                        "rows": rows,
                    }
                )
        payload = generate_school_analysis_docx(
            analysis,
            school_name=school.name,
            academic_year=selected_year,
            protocol_task_tables=protocol_task_tables,
        )

        year_part = f"_{selected_year}" if selected_year else ""
        code = (school.code or str(school.pk)).replace(" ", "_")
        filename = f"vpr_school_analytics_{code}{year_part}.docx"
        response = FileResponse(
            payload,
            as_attachment=True,
            filename=filename,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        return response
