/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

class MiniAnalyticsDashboard extends Component {
    static template = "mini_analytics_dashboard.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            period: "month",
            loading: true,
            data: {
                kpis: {
                    revenue: 0, total_orders: 0, total_customers: 0,
                    aov: 0, conv_rate: 0, cancel_rate: 0,
                    total_stock: 0, low_stock_count: 0,
                },
                charts: {
                    sales_trend: [], status_data: [],
                    product_revenue: [], customer_growth: [], funnel: [],
                },
                tables: { top_customers: [], recent_orders: [] },
            },
            reportDateFrom: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0],
            reportDateTo: new Date().toISOString().split('T')[0],
            sendingReport: false,
            reportMessage: '',
            reportSuccess: false,
        });
        this._charts = {};

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            await this.loadData();
        });

        onMounted(() => {
            this.renderAllCharts();
        });
        // onMounted(() => {
        //     this.el.closest(".o_action")?.classList.add("mini-dash-action");
        //     this.renderAllCharts();
        // });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const result = await this.orm.call(
                "mini.dashboard", "get_dashboard_data", [this.state.period]
            );
            this.state.data = result;
        } catch (e) {
            console.error("Dashboard load error:", e);
        }
        this.state.loading = false;
    }

    async onPeriodChange(period) {
        this.state.period = period;
        await this.loadData();
        this.renderAllCharts();
    }

    async onRefresh() {
        await this.loadData();
        this.renderAllCharts();
    }

    async onSendReport() {
        const { reportDateFrom, reportDateTo } = this.state;
        if (!reportDateFrom || !reportDateTo) {
            this.state.reportSuccess = false;
            this.state.reportMessage = 'Please select both From and To dates.';
            return;
        }
        if (reportDateFrom > reportDateTo) {
            this.state.reportSuccess = false;
            this.state.reportMessage = 'From date cannot be after To date.';
            return;
        }
        this.state.sendingReport = true;
        this.state.reportMessage = '';
        try {
            const result = await this.orm.call(
                'mini.dashboard', 'send_report_email',
                [reportDateFrom, reportDateTo]
            );
            this.state.reportSuccess = true;
            this.state.reportMessage = result.message || 'Report sent successfully!';
        } catch (e) {
            this.state.reportSuccess = false;
            this.state.reportMessage = 'Failed to send report: ' + (e.message || e.data?.message || 'Unknown error');
        }
        this.state.sendingReport = false;
    }

    formatCurrency(val) {
        if (val === undefined || val === null) return "₹0";
        return "₹" + Number(val).toLocaleString("en-IN", { maximumFractionDigits: 0 });
    }

    formatPercent(val) {
        if (val === undefined || val === null) return "0%";
        return Number(val).toFixed(1) + "%";
    }

    // ─── Chart Rendering ───────────────────────────────

    renderAllCharts() {
        this._renderLineChart(
            "salesTrendCanvas",
            this.state.data.charts.sales_trend,
            "Revenue Trend", "#714B67"
        );
        this._renderBarChart(
            "orderStatusCanvas",
            this.state.data.charts.status_data,
            "Orders"
        );
        this._renderDoughnutChart(
            "productRevenueCanvas",
            this.state.data.charts.product_revenue
        );
        this._renderBarChart(
            "customerGrowthCanvas",
            this.state.data.charts.customer_growth,
            "New Customers", "#3498db"
        );
        this._renderHorizontalBar(
            "funnelCanvas",
            this.state.data.charts.funnel,
            "Conversion Funnel"
        );
    }

    _destroyChart(id) {
        if (this._charts[id]) {
            this._charts[id].destroy();
            delete this._charts[id];
        }
    }

    _renderLineChart(canvasId, data, label, color) {
        const el = document.getElementById(canvasId);
        if (!el) return;
        this._destroyChart(canvasId);
        this._charts[canvasId] = new Chart(el, {
            type: "line",
            data: {
                labels: data.map((d) => d.label),
                datasets: [{
                    label: label,
                    data: data.map((d) => d.value),
                    borderColor: color || "#714B67",
                    backgroundColor: (color || "#714B67") + "22",
                    fill: true, tension: 0.4, pointRadius: 4,
                    pointBackgroundColor: color || "#714B67",
                }],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: "#f0f0f0" } },
                    x: { grid: { display: false } },
                },
            },
        });
    }

    _renderBarChart(canvasId, data, label, singleColor) {
        const el = document.getElementById(canvasId);
        if (!el) return;
        this._destroyChart(canvasId);
        const colors = data.map((d) => d.color || singleColor || "#3498db");
        this._charts[canvasId] = new Chart(el, {
            type: "bar",
            data: {
                labels: data.map((d) => d.label),
                datasets: [{
                    label: label || "Count",
                    data: data.map((d) => d.value),
                    backgroundColor: colors,
                    borderRadius: 6,
                }],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: "#f0f0f0" } },
                    x: { grid: { display: false } },
                },
            },
        });
    }

    _renderDoughnutChart(canvasId, data) {
        const el = document.getElementById(canvasId);
        if (!el) return;
        this._destroyChart(canvasId);
        const palette = ["#1abc9c", "#3498db", "#9b59b6", "#e67e22", "#e74c3c", "#2ecc71", "#f1c40f", "#34495e"];
        this._charts[canvasId] = new Chart(el, {
            type: "doughnut",
            data: {
                labels: data.map((d) => d.label),
                datasets: [{
                    data: data.map((d) => d.value),
                    backgroundColor: palette.slice(0, data.length),
                    borderWidth: 2, borderColor: "#fff",
                }],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { position: "bottom", labels: { padding: 12, usePointStyle: true } },
                },
            },
        });
    }

    _renderHorizontalBar(canvasId, data, label) {
        const el = document.getElementById(canvasId);
        if (!el) return;
        this._destroyChart(canvasId);
        const colors = ["#f39c12", "#27ae60", "#e74c3c"];
        this._charts[canvasId] = new Chart(el, {
            type: "bar",
            data: {
                labels: data.map((d) => d.label),
                datasets: [{
                    label: label,
                    data: data.map((d) => d.value),
                    backgroundColor: colors.slice(0, data.length),
                    borderRadius: 6,
                }],
            },
            options: {
                indexAxis: "y",
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { beginAtZero: true, grid: { color: "#f0f0f0" } },
                    y: { grid: { display: false } },
                },
            },
        });
    }


}

registry.category("actions").add("mini_analytics_dashboard", MiniAnalyticsDashboard);
