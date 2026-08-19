"""Справочник заданий ВПР: список, карточка, CRUD, импорт."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
)

from apps.vpr.exceptions import VprCatalogImportError
from apps.vpr.forms import VprTaskCatalogEntryForm, VprTaskCatalogImportForm
from apps.vpr.models import VprTaskCatalogEntry
from apps.vpr.services.catalog_import import import_catalog_file
from apps.vpr.services.catalog_registry import build_catalog_list

logger = logging.getLogger(__name__)


def can_manage_catalog(user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return getattr(user, "role", None) in {"district", "ministry"}


def can_view_catalog(user) -> bool:
    if not user.is_authenticated:
        return False
    if can_manage_catalog(user):
        return True
    return getattr(user, "role", None) in {"school", "district", "ministry"}


class CatalogAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = False

    def test_func(self):
        return can_view_catalog(self.request.user)

    def handle_no_permission(self):
        return redirect("cabinet")


class CatalogManageMixin(CatalogAccessMixin):
    def test_func(self):
        return can_manage_catalog(self.request.user)


class VprTaskCatalogListView(CatalogAccessMixin, ListView):
    template_name = "vpr/catalog_list.html"
    context_object_name = "entries"

    def get_queryset(self):
        return VprTaskCatalogEntry.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = build_catalog_list(self.request.GET)
        context.update(data)
        context["can_manage"] = can_manage_catalog(self.request.user)
        params = self.request.GET.copy()
        params.pop("page", None)
        context["querystring"] = params.urlencode()
        return context


class VprTaskCatalogDetailView(CatalogAccessMixin, DetailView):
    template_name = "vpr/catalog_detail.html"
    model = VprTaskCatalogEntry
    pk_url_kwarg = "entry_id"
    context_object_name = "entry"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_manage"] = can_manage_catalog(self.request.user)
        return context


class VprTaskCatalogCreateView(CatalogManageMixin, CreateView):
    template_name = "vpr/catalog_form.html"
    model = VprTaskCatalogEntry
    form_class = VprTaskCatalogEntryForm

    def get_success_url(self):
        return reverse("vpr-catalog-detail", kwargs={"entry_id": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Запись справочника создана.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_title"] = "Новое задание ВПР"
        context["can_manage"] = True
        return context


class VprTaskCatalogUpdateView(CatalogManageMixin, UpdateView):
    template_name = "vpr/catalog_form.html"
    model = VprTaskCatalogEntry
    form_class = VprTaskCatalogEntryForm
    pk_url_kwarg = "entry_id"

    def get_success_url(self):
        return reverse("vpr-catalog-detail", kwargs={"entry_id": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Запись справочника обновлена.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_title"] = f"Редактирование · №{self.object.display_code}"
        context["can_manage"] = True
        return context


class VprTaskCatalogDeleteView(CatalogManageMixin, DeleteView):
    template_name = "vpr/catalog_confirm_delete.html"
    model = VprTaskCatalogEntry
    pk_url_kwarg = "entry_id"
    success_url = reverse_lazy("vpr-catalog-list")
    context_object_name = "entry"

    def form_valid(self, form):
        messages.success(self.request, "Запись справочника удалена.")
        return super().form_valid(form)


class VprTaskCatalogImportView(CatalogManageMixin, FormView):
    template_name = "vpr/catalog_import.html"
    form_class = VprTaskCatalogImportForm
    success_url = reverse_lazy("vpr-catalog-list")

    def form_valid(self, form):
        uploaded = form.cleaned_data["file"]
        suffix = Path(uploaded.name).suffix.lower()
        if suffix not in {".json", ".csv", ".xlsx", ".xlsm"}:
            messages.error(self.request, "Поддерживаются только JSON, CSV и Excel (.xlsx).")
            return redirect("vpr-catalog-import")

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                for chunk in uploaded.chunks():
                    tmp.write(chunk)
                tmp_path = Path(tmp.name)
            record, stats = import_catalog_file(
                tmp_path,
                user=self.request.user,
                store_file=True,
                uploaded_file=uploaded,
            )
            if stats.status == "failed":
                messages.error(self.request, record.message)
            elif stats.errors:
                messages.warning(self.request, record.message)
            else:
                messages.success(self.request, record.message)
        except VprCatalogImportError as exc:
            messages.error(self.request, str(exc))
            return redirect("vpr-catalog-import")
        except Exception as exc:  # noqa: BLE001
            logger.exception("VPR catalog import failed")
            messages.error(self.request, f"Ошибка импорта справочника: {exc}")
            return redirect("vpr-catalog-import")
        finally:
            if tmp_path and tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
        return redirect("vpr-catalog-list")
