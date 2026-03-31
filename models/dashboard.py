from odoo import models, fields, api
from datetime import datetime, timedelta
from collections import defaultdict


class MiniDashboard(models.Model):
    _name = 'mini.dashboard'
    _description = 'Mini Analytics Dashboard Data Provider'

    name = fields.Char(default='Dashboard')

    @api.model
    def get_dashboard_data(self, period='month'):
        """Main entry point. Returns KPIs, chart data, and table data."""
        domain = self._get_date_domain(period)

        kpis = self._get_kpis(domain)
        charts = self._get_chart_data(domain)
        tables = self._get_table_data(domain)

        return {
            'kpis': kpis,
            'charts': charts,
            'tables': tables,
        }

    # ─── Helpers ───────────────────────────────────────────────

    def _get_date_domain(self, period):
        now = fields.Datetime.now()
        if period == 'today':
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'month':
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == 'year':
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return [('date_order', '>=', start)]

    # ─── KPIs ──────────────────────────────────────────────────

    def _get_kpis(self, domain):
        Order = self.env['mini.order']

        all_orders = Order.search(domain)
        total_orders = len(all_orders)

        confirmed_orders = all_orders.filtered(lambda o: o.state == 'confirmed')
        confirmed_count = len(confirmed_orders)
        cancelled_count = len(all_orders.filtered(lambda o: o.state == 'cancel'))

        # Revenue: sum computed field manually
        revenue = sum(confirmed_orders.mapped('total_amount'))

        # Unique customers in period
        total_customers = len(all_orders.mapped('customer_id'))

        aov = (revenue / confirmed_count) if confirmed_count > 0 else 0
        conv_rate = (confirmed_count / total_orders * 100) if total_orders > 0 else 0
        cancel_rate = (cancelled_count / total_orders * 100) if total_orders > 0 else 0

        # Inventory summary
        products = self.env['mini.product'].search([])
        total_stock = sum(products.mapped('quantity'))
        low_stock_count = len(products.filtered(lambda p: p.quantity < 10))

        return {
            'revenue': revenue or 0,
            'total_orders': total_orders,
            'total_customers': total_customers,
            'aov': round(aov, 2),
            'conv_rate': round(conv_rate, 1),
            'cancel_rate': round(cancel_rate, 1),
            'total_stock': total_stock,
            'low_stock_count': low_stock_count,
        }

    # ─── Charts ────────────────────────────────────────────────

    def _get_chart_data(self, domain):
        Order = self.env['mini.order']

        # A. Sales Trend (by day) — manual grouping since total_amount is computed
        confirmed_orders = Order.search(domain + [('state', '=', 'confirmed')])
        trend_map = defaultdict(float)
        for o in confirmed_orders:
            if o.date_order:
                day_label = o.date_order.strftime('%d %b')
                trend_map[day_label] += o.total_amount
        sales_trend = [{'label': k, 'value': v} for k, v in trend_map.items()]

        # B. Orders by Status (count only, so read_group works fine)
        status_raw = Order.read_group(domain, ['state'], ['state'])
        status_map = {'draft': 'Draft', 'confirmed': 'Confirmed', 'cancel': 'Cancelled'}
        status_colors = {'draft': '#f39c12', 'confirmed': '#27ae60', 'cancel': '#e74c3c'}
        status_data = [
            {
                'label': status_map.get(r['state'], r['state']),
                'value': r['state_count'],
                'color': status_colors.get(r['state'], '#95a5a6'),
            }
            for r in status_raw
        ]

        # C. Revenue by Product — manual since subtotal is computed
        product_map = defaultdict(float)
        for o in confirmed_orders:
            for line in o.order_line_ids:
                pname = line.product_id.name if line.product_id else 'Unknown'
                product_map[pname] += line.subtotal or 0
        product_revenue = [{'label': k, 'value': v} for k, v in product_map.items()]

        # D. Customer Growth (new customers by month — count only, works with read_group)
        cust_raw = self.env['mini.customer'].read_group(
            [],
            ['create_date'],
            ['create_date:month'],
        )
        customer_growth = [
            {'label': r['create_date:month'] or 'N/A', 'value': r['create_date_count']}
            for r in cust_raw
        ]

        # E. Conversion Funnel
        confirmed = Order.search_count(domain + [('state', '=', 'confirmed')])
        cancelled = Order.search_count(domain + [('state', '=', 'cancel')])
        draft = Order.search_count(domain + [('state', '=', 'draft')])
        funnel = [
            {'label': 'Draft', 'value': draft},
            {'label': 'Confirmed', 'value': confirmed},
            {'label': 'Cancelled', 'value': cancelled},
        ]

        return {
            'sales_trend': sales_trend,
            'status_data': status_data,
            'product_revenue': product_revenue,
            'customer_growth': customer_growth,
            'funnel': funnel,
        }

    # ─── Tables ────────────────────────────────────────────────

    def _get_table_data(self, domain):
        Order = self.env['mini.order']

        # Top customers — manual grouping since total_amount is computed
        confirmed_orders = Order.search(domain + [('state', '=', 'confirmed')])
        cust_totals = defaultdict(float)
        for o in confirmed_orders:
            cust_totals[o.customer_id.name or 'Unknown'] += o.total_amount
        top_customers = sorted(
            [{'name': k, 'amount': v} for k, v in cust_totals.items()],
            key=lambda x: x['amount'],
            reverse=True,
        )[:5]

        # Recent orders
        recent_recs = Order.search(domain, order='date_order DESC', limit=10)
        recent_orders = []
        for o in recent_recs:
            recent_orders.append({
                'name': o.name or '',
                'customer': o.customer_id.name or '',
                'amount': o.total_amount or 0,
                'date': o.date_order.strftime('%Y-%m-%d %H:%M') if o.date_order else '',
                'state': o.state or '',
            })

        return {
            'top_customers': top_customers,
            'recent_orders': recent_orders,
        }

    # ─── Email Report ──────────────────────────────────────────

    @api.model
    def send_monthly_report_cron(self):
        """Called by ir.cron on 1st of each month. Sends previous month report."""
        now = fields.Datetime.now()
        # Calculate previous month range
        first_of_current = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_of_prev = first_of_current - timedelta(days=1)
        first_of_prev = last_of_prev.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        month_name = last_of_prev.strftime('%B %Y')
        domain = [('date_order', '>=', first_of_prev), ('date_order', '<=', last_of_prev)]

        self._generate_and_send_report(domain, month_name)

    @api.model
    def send_report_email(self, date_from, date_to):
        """Called manually from the dashboard Generate Report button."""
        from datetime import datetime as dt
        start = dt.strptime(date_from, '%Y-%m-%d')
        end = dt.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        label = f"{start.strftime('%d %b %Y')} – {end.strftime('%d %b %Y')}"
        domain = [('date_order', '>=', start), ('date_order', '<=', end)]

        self._generate_and_send_report(domain, label)
        return {'success': True, 'message': f'Report for {label} sent successfully!'}

    def _generate_and_send_report(self, domain, period_label):
        """Build HTML report and send via email."""
        kpis = self._get_kpis(domain)
        tables = self._get_table_data(domain)

        html = self._build_report_html(kpis, tables, period_label)

        # Send to admin user
        admin = self.env.ref('base.user_admin')
        email_to = admin.partner_id.email or admin.login

        mail_values = {
            'subject': f'📊 Analytics Report – {period_label}',
            'body_html': html,
            'email_to': email_to,
            'email_from': self.env.company.email or 'noreply@minianalytics.com',
            'auto_delete': True,
        }
        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.send()

    def _build_report_html(self, kpis, tables, period_label):
        """Generate a beautiful HTML email report."""
        # KPI rows
        kpi_items = [
            ('Total Revenue', f"₹{kpis['revenue']:,.0f}", '#667eea'),
            ('Total Orders', str(kpis['total_orders']), '#43e97b'),
            ('Customers', str(kpis['total_customers']), '#4facfe'),
            ('Avg Order Value', f"₹{kpis['aov']:,.2f}", '#fa709a'),
            ('Conversion Rate', f"{kpis['conv_rate']}%", '#27ae60'),
            ('Cancellation Rate', f"{kpis['cancel_rate']}%", '#e74c3c'),
            ('Total Stock', str(kpis['total_stock']), '#6c5ce7'),
            ('Low Stock Items', str(kpis['low_stock_count']), '#e17055'),
        ]

        kpi_html = ''
        for i in range(0, len(kpi_items), 4):
            row_items = kpi_items[i:i+4]
            cells = ''
            for label, value, color in row_items:
                cells += f'''
                <td style="padding:8px;text-align:center;width:25%;">
                    <div style="background:#f8f9fa;border-radius:10px;padding:16px;border-left:4px solid {color};">
                        <div style="font-size:22px;font-weight:700;color:#2c3e50;">{value}</div>
                        <div style="font-size:11px;color:#95a5a6;text-transform:uppercase;letter-spacing:0.5px;margin-top:4px;">{label}</div>
                    </div>
                </td>'''
            kpi_html += f'<tr>{cells}</tr>'

        # Top customers table
        cust_rows = ''
        for i, c in enumerate(tables.get('top_customers', []), 1):
            cust_rows += f'''
            <tr>
                <td style="padding:8px 12px;border-bottom:1px solid #f1f3f5;">{i}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #f1f3f5;font-weight:600;">{c['name']}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #f1f3f5;text-align:right;color:#27ae60;font-weight:600;">₹{c['amount']:,.0f}</td>
            </tr>'''

        # Recent orders table
        order_rows = ''
        for o in tables.get('recent_orders', []):
            state_color = '#27ae60' if o['state'] == 'confirmed' else ('#e74c3c' if o['state'] == 'cancel' else '#f39c12')
            order_rows += f'''
            <tr>
                <td style="padding:8px 12px;border-bottom:1px solid #f1f3f5;font-weight:600;">{o['name']}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #f1f3f5;">{o['customer']}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #f1f3f5;">{o['date']}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #f1f3f5;">
                    <span style="background:{state_color};color:#fff;padding:2px 10px;border-radius:12px;font-size:11px;">{o['state']}</span>
                </td>
                <td style="padding:8px 12px;border-bottom:1px solid #f1f3f5;text-align:right;font-weight:600;">₹{o['amount']:,.0f}</td>
            </tr>'''

        html = f'''
        <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:700px;margin:0 auto;color:#2c3e50;">
            <div style="background:linear-gradient(135deg,#714B67,#9b59b6);padding:30px;border-radius:12px 12px 0 0;text-align:center;">
                <h1 style="color:#fff;margin:0;font-size:24px;">📊 Analytics Report</h1>
                <p style="color:#e8d5e3;margin:8px 0 0;font-size:14px;">{period_label}</p>
            </div>

            <div style="background:#fff;padding:24px;border:1px solid #eee;">
                <h2 style="color:#714B67;font-size:16px;border-bottom:2px solid #f1f3f5;padding-bottom:8px;">Key Performance Indicators</h2>
                <table style="width:100%;border-collapse:collapse;">
                    {kpi_html}
                </table>

                <h2 style="color:#714B67;font-size:16px;border-bottom:2px solid #f1f3f5;padding-bottom:8px;margin-top:28px;">🏆 Top Customers</h2>
                <table style="width:100%;border-collapse:collapse;font-size:13px;">
                    <tr style="background:#f8f9fa;">
                        <th style="padding:8px 12px;text-align:left;">#</th>
                        <th style="padding:8px 12px;text-align:left;">Customer</th>
                        <th style="padding:8px 12px;text-align:right;">Revenue</th>
                    </tr>
                    {cust_rows or '<tr><td colspan="3" style="padding:12px;text-align:center;color:#95a5a6;">No data</td></tr>'}
                </table>

                <h2 style="color:#714B67;font-size:16px;border-bottom:2px solid #f1f3f5;padding-bottom:8px;margin-top:28px;">📋 Recent Orders</h2>
                <table style="width:100%;border-collapse:collapse;font-size:13px;">
                    <tr style="background:#f8f9fa;">
                        <th style="padding:8px 12px;text-align:left;">Order</th>
                        <th style="padding:8px 12px;text-align:left;">Customer</th>
                        <th style="padding:8px 12px;text-align:left;">Date</th>
                        <th style="padding:8px 12px;text-align:left;">Status</th>
                        <th style="padding:8px 12px;text-align:right;">Amount</th>
                    </tr>
                    {order_rows or '<tr><td colspan="5" style="padding:12px;text-align:center;color:#95a5a6;">No data</td></tr>'}
                </table>
            </div>

            <div style="background:#f8f9fa;padding:16px;border-radius:0 0 12px 12px;text-align:center;border:1px solid #eee;border-top:none;">
                <p style="margin:0;font-size:12px;color:#95a5a6;">Generated by Mini Analytics Dashboard • {fields.Datetime.now().strftime('%d %b %Y %H:%M')}</p>
            </div>
        </div>
        '''
        return html

