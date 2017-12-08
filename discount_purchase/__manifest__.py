# -*- coding: utf-8 -*-
{
    'name': 'Discount Purchase Management',
    'version': '11.0.0.1.0',
    'author': 'Yusuf Danny W.',
    'category': 'Purchases',
    'summary': 'Incremental Discount in Purchase Order',
    'description': """
    Incremental Discount via button in purchase line after create purchase order
    """,
    'depends': ['purchase'],
    'data' : [
        'security/ir.model.access.csv',
        'views/discount_purchase_views.xml',
        'views/purchase_views.xml',
        'views/account_invoice_views.xml',
    ],
    'installable': True,
    'application' : False,
    'auto_install' : False,
}
