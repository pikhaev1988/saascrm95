from django.urls import path

from apps.vpr.views import (
    VprConfirmImportView,
    VprImportResultView,
    VprPreviewView,
    VprSampleDownloadView,
    VprUploadView,
)
from apps.vpr.views_catalog import (
    VprTaskCatalogCreateView,
    VprTaskCatalogDeleteView,
    VprTaskCatalogDetailView,
    VprTaskCatalogImportView,
    VprTaskCatalogListView,
    VprTaskCatalogUpdateView,
)
from apps.vpr.views_conclusion import VprProtocolConclusionView
from apps.vpr.views_overview import VprProtocolOverviewDocxView, VprProtocolOverviewView
from apps.vpr.views_school_analytics import VprSchoolAnalyticsDocxView, VprSchoolAnalyticsView
from apps.vpr.views_registry import (
    VprProtocolDetailView,
    VprProtocolInfoView,
    VprProtocolRegistryView,
    VprUploadDeleteView,
    VprUploadFileDownloadView,
    VprUploadReimportView,
)

urlpatterns = [
    path("school/", VprSchoolAnalyticsView.as_view(), name="vpr-school-analytics"),
    path(
        "school/export-docx/",
        VprSchoolAnalyticsDocxView.as_view(),
        name="vpr-school-analytics-docx",
    ),
    path("catalog/", VprTaskCatalogListView.as_view(), name="vpr-catalog-list"),
    path("catalog/new/", VprTaskCatalogCreateView.as_view(), name="vpr-catalog-create"),
    path("catalog/import/", VprTaskCatalogImportView.as_view(), name="vpr-catalog-import"),
    path(
        "catalog/<int:entry_id>/",
        VprTaskCatalogDetailView.as_view(),
        name="vpr-catalog-detail",
    ),
    path(
        "catalog/<int:entry_id>/edit/",
        VprTaskCatalogUpdateView.as_view(),
        name="vpr-catalog-edit",
    ),
    path(
        "catalog/<int:entry_id>/delete/",
        VprTaskCatalogDeleteView.as_view(),
        name="vpr-catalog-delete",
    ),
    path("protocols/", VprProtocolRegistryView.as_view(), name="vpr-registry"),
    path(
        "protocols/<int:protocol_id>/",
        VprProtocolDetailView.as_view(),
        name="vpr-protocol-detail",
    ),
    path(
        "protocols/<int:protocol_id>/overview/",
        VprProtocolOverviewView.as_view(),
        name="vpr-protocol-overview",
    ),
    path(
        "protocols/<int:protocol_id>/overview/export-docx/",
        VprProtocolOverviewDocxView.as_view(),
        name="vpr-protocol-overview-docx",
    ),
    path(
        "protocols/<int:protocol_id>/conclusion/",
        VprProtocolConclusionView.as_view(),
        name="vpr-protocol-conclusion",
    ),
    path(
        "protocols/<int:protocol_id>/info/",
        VprProtocolInfoView.as_view(),
        name="vpr-protocol-info",
    ),
    path(
        "uploads/<int:upload_id>/file/",
        VprUploadFileDownloadView.as_view(),
        name="vpr-upload-file",
    ),
    path(
        "uploads/<int:upload_id>/delete/",
        VprUploadDeleteView.as_view(),
        name="vpr-upload-delete",
    ),
    path(
        "uploads/<int:upload_id>/reimport/",
        VprUploadReimportView.as_view(),
        name="vpr-upload-reimport",
    ),
    path("upload/", VprUploadView.as_view(), name="vpr-upload"),
    path("upload/sample/", VprSampleDownloadView.as_view(), name="vpr-upload-sample"),
    path("upload/<int:upload_id>/preview/", VprPreviewView.as_view(), name="vpr-preview"),
    path(
        "upload/<int:upload_id>/confirm/",
        VprConfirmImportView.as_view(),
        name="vpr-confirm",
    ),
    path("upload/<int:upload_id>/result/", VprImportResultView.as_view(), name="vpr-result"),
]
