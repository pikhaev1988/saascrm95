/**
 * Design System — Chart.js defaults (presentation only).
 * Unified colors, grid, tooltips, fonts for all cabinets.
 */
(function () {
    var DS_CHART = {
        colors: [
            "#2563eb",
            "#06b6d4",
            "#16a34a",
            "#dc2626",
            "#7c3aed",
            "#db2777",
            "#d97706",
            "#ea580c",
            "#64748b"
        ],
        grid: "#eef2f7",
        text: "#64748b",
        border: "#ffffff",
        fontFamily: '"Inter", "Manrope", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    };

    window.DS_CHART = DS_CHART;

    function applyChartDefaults() {
        if (!window.Chart || !window.Chart.defaults) return;
        var d = window.Chart.defaults;
        d.font.family = DS_CHART.fontFamily;
        d.font.size = 11;
        d.color = DS_CHART.text;
        d.plugins = d.plugins || {};
        d.plugins.legend = d.plugins.legend || {};
        d.plugins.legend.labels = Object.assign({}, d.plugins.legend.labels || {}, {
            boxWidth: 12,
            boxHeight: 12,
            usePointStyle: true,
            padding: 14
        });
        d.plugins.tooltip = d.plugins.tooltip || {};
        Object.assign(d.plugins.tooltip, {
            backgroundColor: "rgba(15, 23, 42, 0.92)",
            titleColor: "#fff",
            bodyColor: "#e2e8f0",
            cornerRadius: 8,
            padding: 10,
            displayColors: true
        });
        if (d.scale) {
            d.scale.grid = Object.assign({}, d.scale.grid || {}, { color: DS_CHART.grid });
        }
        if (d.scales) {
            ["category", "linear", "logarithmic", "time", "timeseries"].forEach(function (key) {
                if (!d.scales[key]) return;
                d.scales[key].grid = Object.assign({}, d.scales[key].grid || {}, {
                    color: DS_CHART.grid,
                    drawBorder: false
                });
                d.scales[key].ticks = Object.assign({}, d.scales[key].ticks || {}, {
                    color: DS_CHART.text,
                    font: { size: 10, family: DS_CHART.fontFamily }
                });
            });
        }
        d.elements = d.elements || {};
        d.elements.line = Object.assign({}, d.elements.line || {}, {
            borderWidth: 2,
            tension: 0.35
        });
        d.elements.point = Object.assign({}, d.elements.point || {}, {
            radius: 3,
            hoverRadius: 5
        });
        d.elements.bar = Object.assign({}, d.elements.bar || {}, {
            borderRadius: 8,
            maxBarThickness: 28
        });
        d.animation = Object.assign({}, d.animation || {}, {
            duration: 450,
            easing: "easeOutQuart"
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", applyChartDefaults);
    } else {
        applyChartDefaults();
    }
    // Chart.js may load with defer — retry shortly
    setTimeout(applyChartDefaults, 0);
    setTimeout(applyChartDefaults, 300);
})();
