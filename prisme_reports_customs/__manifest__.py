# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Prisme Reports Customs',
    'version': '1.0',
    'summary': 'Add customs information on sale order, invoice and picking reports.',
    'description': """
        Add customs information on sale order, invoice and picking reports.
    """,
    'category': 'Reporting',
    'author': 'Prisme Solutions Informatique SA',
    'website': 'https://www.prisme.ch',
    'depends': ['account', 'sale_management', 'delivery'],
    'data': [
        'views/product_view.xml',
        'report/report_stock_picking.xml',
        'report/report_deliveryslip.xml',
        'report/report_invoice.xml',
        'report/sale_report.xml',
        'views/stock_picking_view.xml',
        'report/report_delivery_document.xml'
    ],
    'demo': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
