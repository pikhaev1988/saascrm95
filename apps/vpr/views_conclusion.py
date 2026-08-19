"""Экран «Аналитическое заключение» ВПР — данные только из комплексного анализа."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import DetailView

from apps.vpr.access import can_access_protocol
from apps.vpr.comprehensive_analysis import get_protocol_analysis
from apps.vpr.models import VprProtocol


class VprProtocolConclusionView(LoginRequiredMixin, DetailView):
    """
    Официальное аналитическое заключение по протоколу ВПР.
    View только получает analysis и отображает analysis.conclusion.
    """

    template_name = "vpr/protocol_conclusion.html"
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
        context.update(
            {
                "upload": protocol.upload,
                "user_role": getattr(self.request.user, "role", None),
                "active_tab": "conclusion",
                "analysis": analysis,
            }
        )
        return context
