{
    'name': 'Mini Analytics Dashboard',
    'version': '1.0',
    'summary': 'Business Intelligence Dashboard for Mini Modules',
    'author': 'Arjun',
    'category': 'Analytics',
    'sequence': 15,
    'depends': ['base', 'web', 'mail', 'mini_sales', 'mini_inventory', 'mini_purchase', 'mini_accounting'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mini_analytics_dashboard/static/src/css/dashboard.css',
            'mini_analytics_dashboard/static/src/xml/dashboard_template.xml',
            'mini_analytics_dashboard/static/src/js/dashboard.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
