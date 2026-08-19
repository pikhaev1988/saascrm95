(function () {
    "use strict";

    var activeDownload = null;

    function ensureStatusBanner() {
        var box = document.getElementById("download-status-banner");
        if (box) {
            return box;
        }
        box = document.createElement("div");
        box.id = "download-status-banner";
        box.className = "download-status-banner download-status-banner--info";
        box.setAttribute("role", "status");
        box.setAttribute("aria-live", "polite");
        box.hidden = true;

        var text = document.createElement("p");
        text.id = "download-status-text";
        text.className = "download-status-banner__text";
        box.appendChild(text);

        var action = document.createElement("button");
        action.type = "button";
        action.id = "download-status-action";
        action.className = "ui-btn ui-btn-primary download-status-banner__action";
        action.hidden = true;
        action.textContent = "Скачать готовый файл";
        box.appendChild(action);

        var anchor = document.querySelector(".app-main-inner") || document.getElementById("main-content") || document.body;
        anchor.insertBefore(box, anchor.firstChild);
        return box;
    }

    function revealBanner() {
        var box = ensureStatusBanner();
        box.hidden = false;
    }

    function getStatusTextEl() {
        ensureStatusBanner();
        return document.getElementById("download-status-text");
    }

    function getStatusActionEl() {
        ensureStatusBanner();
        return document.getElementById("download-status-action");
    }

    function showStatus(message, type) {
        var box = ensureStatusBanner();
        var text = getStatusTextEl();
        box.className = "download-status-banner download-status-banner--" + (type || "info");
        text.textContent = message;
        revealBanner();
    }

    function hideStatus(delayMs) {
        var box = document.getElementById("download-status-banner");
        var action = getStatusActionEl();
        if (!box) {
            return;
        }
        if (action) {
            action.hidden = true;
            action.onclick = null;
            action.classList.remove("download-status-banner__action--pulse");
        }
        if (delayMs) {
            window.setTimeout(function () {
                box.hidden = true;
            }, delayMs);
            return;
        }
        box.hidden = true;
    }

    function formatSize(bytes) {
        if (!bytes) {
            return "";
        }
        if (bytes < 1024) {
            return bytes + " Б";
        }
        return Math.round(bytes / 1024) + " КБ";
    }

    function parseFilename(disposition, fallback) {
        if (!disposition) {
            return fallback;
        }
        var utfMatch = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
        if (utfMatch) {
            try {
                return decodeURIComponent(utfMatch[1].replace(/"/g, ""));
            } catch (e) {
                return utfMatch[1];
            }
        }
        var match = /filename="?([^";]+)"?/i.exec(disposition);
        return match ? match[1] : fallback;
    }

    function defaultFilename(url) {
        if (url.indexOf("export-pdf") !== -1) {
            return "analysis.pdf";
        }
        if (url.indexOf("export-xlsx") !== -1) {
            return "analysis.xlsx";
        }
        if (url.indexOf("export-pptx") !== -1) {
            return "analysis.pptx";
        }
        return "analysis.docx";
    }

    function getDownloadUrl(trigger) {
        return (
            trigger.getAttribute("data-download-url") ||
            trigger.getAttribute("href") ||
            ""
        ).trim();
    }

    function getTriggerLabel(trigger) {
        return trigger.getAttribute("data-download-label") || trigger.textContent.trim();
    }

    function setAllTriggersLoading(loading) {
        document.querySelectorAll(".js-download-in-place").forEach(function (trigger) {
            if (loading) {
                if (!trigger.dataset.downloadIdleLabel) {
                    trigger.dataset.downloadIdleLabel = getTriggerLabel(trigger);
                }
                trigger.setAttribute("aria-busy", "true");
                trigger.classList.add("is-download-loading");
                trigger.disabled = true;
                if (trigger === (activeDownload && activeDownload.trigger)) {
                    trigger.textContent = "Подготовка…";
                } else {
                    trigger.textContent = "Ожидание…";
                }
            } else {
                trigger.removeAttribute("aria-busy");
                trigger.classList.remove("is-download-loading");
                trigger.disabled = false;
                trigger.textContent = trigger.dataset.downloadIdleLabel || getTriggerLabel(trigger);
            }
        });
    }

    function saveBlobWithUserGesture(blob, filename) {
        var objectUrl = URL.createObjectURL(blob);
        var anchor = document.createElement("a");
        anchor.href = objectUrl;
        anchor.download = filename;
        anchor.style.display = "none";
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        window.setTimeout(function () {
            URL.revokeObjectURL(objectUrl);
        }, 2000);
    }

    function offerManualDownload(blob, filename) {
        var action = getStatusActionEl();
        if (!action) {
            return;
        }
        action.hidden = false;
        action.classList.add("download-status-banner__action--pulse");
        action.onclick = function () {
            saveBlobWithUserGesture(blob, filename);
            showStatus("Загрузка начата. Проверьте папку «Загрузки».", "success");
            action.hidden = true;
            action.classList.remove("download-status-banner__action--pulse");
            hideStatus(12000);
        };
        window.setTimeout(function () {
            action.focus();
        }, 100);
    }

    function finishDownload(blob, filename) {
        saveBlobWithUserGesture(blob, filename);
        showStatus("Загрузка начата. Проверьте папку «Загрузки».", "success");
        hideStatus(3500);
    }

    async function startDownload(url, trigger) {
        if (!url || url === "#") {
            return;
        }
        if (activeDownload) {
            showStatus("Отчёт уже формируется. Подождите завершения текущей загрузки.", "info");
            return;
        }

        var originalText = getTriggerLabel(trigger);
        var abortController = typeof AbortController !== "undefined" ? new AbortController() : null;

        var action = getStatusActionEl();
        if (action) {
            action.hidden = true;
            action.onclick = null;
            action.classList.remove("download-status-banner__action--pulse");
        }

        activeDownload = {
            trigger: trigger,
            originalText: originalText,
            abortController: abortController,
        };
        setAllTriggersLoading(true);
        if (activeDownload.trigger) {
            activeDownload.trigger.textContent = "Подготовка…";
        }
        hideStatus(0);

        try {
            var fetchOptions = {
                method: "GET",
                credentials: "same-origin",
            };
            if (abortController) {
                fetchOptions.signal = abortController.signal;
            }
            var response = await fetch(url, fetchOptions);
            var contentType = (response.headers.get("Content-Type") || "").toLowerCase();
            if (!response.ok || contentType.indexOf("text/html") !== -1) {
                throw new Error(
                    "Не удалось сформировать отчёт. Убедитесь, что выбран экзамен и есть данные."
                );
            }
            var blob = await response.blob();
            if (!blob || !blob.size) {
                throw new Error("Сервер вернул пустой файл.");
            }
            var filename = parseFilename(
                response.headers.get("Content-Disposition"),
                defaultFilename(url)
            );
            finishDownload(blob, filename);
        } catch (error) {
            if (error && error.name === "AbortError") {
                return;
            }
            showStatus(
                error && error.message ? error.message : "Ошибка при формировании отчёта.",
                "error"
            );
            hideStatus(15000);
        } finally {
            setAllTriggersLoading(false);
            activeDownload = null;
        }
    }

    document.addEventListener("click", function (event) {
        var trigger = event.target.closest(".js-download-in-place");
        if (!trigger || trigger.disabled) {
            return;
        }
        var url = getDownloadUrl(trigger);
        if (!url || url === "#") {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        startDownload(url, trigger);
    });
})();
