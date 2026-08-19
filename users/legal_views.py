from pathlib import Path

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from users.http_utils import attachment_response
from users.legal import (
    ACCESS_YEARS,
    OPERATOR_EMAIL,
    OPERATOR_INN,
    OPERATOR_NAME,
    OPERATOR_STATUS,
    POLICY_DATE,
    PRODUCT_NAME,
    SCHOOL_DOCUMENTS,
    SCHOOL_DOCUMENTS_DIR,
    SITE_URL,
)


def _school_doc_path(filename: str) -> Path:
    candidates = [
        SCHOOL_DOCUMENTS_DIR / filename,
        Path(settings.BASE_DIR) / "staticfiles" / "docs" / "school" / filename,
    ]
    for path in candidates:
        if path.is_file():
            return path
    return SCHOOL_DOCUMENTS_DIR / filename


class LegalPageView(TemplateView):
    extra_context = {
        "operator_name": OPERATOR_NAME,
        "operator_inn": OPERATOR_INN,
        "operator_status": OPERATOR_STATUS,
        "operator_email": OPERATOR_EMAIL,
        "site_url": SITE_URL,
        "product_name": PRODUCT_NAME,
        "policy_date": POLICY_DATE,
        "access_years": ACCESS_YEARS,
    }


class PrivacyPolicyView(LegalPageView):
    template_name = "legal/privacy.html"


class TermsOfAccessView(LegalPageView):
    template_name = "legal/terms.html"


class SchoolDocumentsView(LoginRequiredMixin, TemplateView):
    template_name = "users/school_documents.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and getattr(request.user, "role", None) != "school":
            return redirect("cabinet")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        docs = []
        for item in SCHOOL_DOCUMENTS:
            path = _school_doc_path(item["file"])
            row = dict(item)
            row["available"] = path.is_file()
            docs.append(row)
        context.update(
            {
                "school_documents": docs,
                "operator_name": OPERATOR_NAME,
                "operator_inn": OPERATOR_INN,
                "operator_email": OPERATOR_EMAIL,
                "site_url": SITE_URL,
                "product_name": PRODUCT_NAME,
                "access_years": ACCESS_YEARS,
            }
        )
        return context


class SchoolDocumentDownloadView(LoginRequiredMixin, View):
    def get(self, request, slug: str):
        if getattr(request.user, "role", None) != "school":
            return redirect("cabinet")
        item = next((row for row in SCHOOL_DOCUMENTS if row["slug"] == slug), None)
        if item is None:
            raise Http404("Документ не найден")
        path = _school_doc_path(item["file"])
        if not path.is_file():
            raise Http404("Файл документа ещё не загружен")
        data = path.read_bytes()
        return attachment_response(
            data,
            item["download_name"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
