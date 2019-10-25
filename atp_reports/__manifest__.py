# *- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

{
    'name': 'ATP Reports',
    'summary': """ 
        Add customs information(Bank Details, CR Grouping) and modifications on sale order, invoice, purchase and picking reports. 
    """,
    'description': """
        Add customs information(Bank Details, CR Grouping) and modifications on sale order, invoice, purchase and picking reports.
    """,
    'author': 'Prisme Solutions Informatique SA',
    'website': 'https://www.prisme.ch',
    'category': 'Reporting',
    'version': '2.0',
    'depends': ['prisme_reports_customs',],
    'data': [
        'views/product_view.xml',
        'views/account_invoice_view.xml',
        'views/sale_view.xml',
        'report/report_invoice.xml',
        'report/sale_report.xml',
        'report/report_purchase.xml',
 
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}