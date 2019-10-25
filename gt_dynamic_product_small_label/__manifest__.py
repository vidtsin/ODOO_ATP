# -*- encoding: utf-8 -*-
##############################################################################
#
#    Authors: Globalteckz, 
#    Copyright Globalteckz 2013
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Dynamic Product Small Label',
	"version": "1.0",
	'summary': 'This module will help to generate product small labels dynamically as per you configure it.',
    'description': """
        You can design template from form view as well as define the sequence for label report.
        You can print label report from Sales order,Purchase order,Invoice,Product and Opertations.
print label
print small label
print barcode
print small barcode
small barcode label
barcode label
product label
product small label
product small barcode
label
print 
humanreadable barcode
human readable barcode
bar code
Barcode
Bar code
Bar Code
barcode template
template barcode
barcode xml
barcode fields
barcode field
barcode currency
dynamic product label
""",
    
    'author': "Globalteckz",
    'category': 'Product',
    'website': 'http://www.globalteckz.com', 
	"price": "69.00",
    "currency": "EUR",
    'images': ['static/description/BANNER.png'],
	#"live_test_url" : "http://dynamiclabel.erpodoo.in:8069",
    "license" : "Other proprietary",
    'depends': ['base','sale_management','purchase','stock','account'],
    'data': [   'security/ir.model.access.csv',
                'reports/label_report.xml',
                'wizards/product_small_label_view.xml',
                'views/data_view.xml',
                'views/label_design_view.xml',
            ],
    # tests order matter
    'test': [
             ],
    'qweb': [
    ],
    'installable': True,
    'application': True,
}
