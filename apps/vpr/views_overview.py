"""Экран «Обзор результатов» ВПР — данные только из VprComprehensiveAnalysisEngine."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView

from apps.vpr.access import can_access_protocol
from apps.vpr.comprehensive_analysis import get_protocol_analysis
from apps.vpr.models import VprProtocol
from apps.vpr.overview_docx import generate_overview_report_docx
from apps.vpr.subject_report import build_subject_report


class VprProtocolOverviewView(LoginRequiredMixin, DetailView):
    """
    Первый аналитический экран ВПР.
    Единственный источник данных — VprComprehensiveAnalysisEngine (через get_protocol_analysis).
    """

    template_name = "vpr/protocol_overview.html"
    model = VprProtocol
    pk_url_kwarg = "protocol_id"
    context_object_name = "protocol"

    def dispatch(self, request, *args, **kwargs):
        protocol = self.get_object()
        if not can_access_protocol(request.user, protocol):
            return redirect("vpr-registry")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return VprProtocol.objects.select_related(
            "upload",
            "upload__uploaded_by",
            "school",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        protocol = self.object
        analysis = get_protocol_analysis(protocol)
        report = build_subject_report(analysis, protocol)
        context.update(
            {
                "upload": protocol.upload,
                "user_role": getattr(self.request.user, "role", None),
                "active_tab": "overview",
                "analysis": analysis,
                "report": report,
            }
        )
        return context


class VprProtocolOverviewDocxView(LoginRequiredMixin, View):
    """Скачать аналитическую справку по предмету/классу."""

    def get(self, request, protocol_id: int, *args, **kwargs):
        protocol = get_object_or_404(
            VprProtocol.objects.select_related("upload", "school"),
            pk=protocol_id,
        )
        if not can_access_protocol(request.user, protocol):
            return redirect("vpr-registry")

        analysis = get_protocol_analysis(protocol)
        report = build_subject_report(analysis, protocol)
        payload = generate_overview_report_docx(analysis, protocol, report=report)

        subject = (protocol.subject or "предмет").replace(" ", "_")
        parallel = protocol.parallel or ""
        year = protocol.academic_year or ""
        filename = f"vpr_spravka_{subject}_{parallel}kl_{year}.docx"
        return FileResponse(
            payload,
            as_attachment=True,
            filename=filename,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
