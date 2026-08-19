from urllib.parse import quote

from django.http import HttpResponse


def attachment_response(data: bytes, filename: str, content_type: str) -> HttpResponse:
    """Ответ для принудительного скачивания файла (в т.ч. в Yandex Browser)."""
    ascii_name = "".join(
        char if char.isascii() and char not in {'"', "\\"} else "_"
        for char in filename
    ).strip("._") or "download"
    utf_name = quote(filename)
    response = HttpResponse(data, content_type=content_type)
    response["Content-Disposition"] = (
        f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{utf_name}'
    )
    response["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response["Pragma"] = "no-cache"
    response["X-Content-Type-Options"] = "nosniff"
    return response
