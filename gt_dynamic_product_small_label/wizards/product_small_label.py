from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, AccessError,RedirectWarning
from odoo.tools.safe_eval import safe_eval
from odoo.tools.misc import find_in_path
from odoo.tools import config
from odoo.sql_db import TestCursor
from odoo.http import request

import time
import base64
import io
import logging
import os
import lxml.html
import tempfile
import subprocess
import re

from lxml import etree
from contextlib import closing
from distutils.version import LooseVersion
from reportlab.graphics.barcode import createBarcodeDrawing
from PyPDF2 import PdfFileWriter, PdfFileReader

_logger = logging.getLogger(__name__)

def _get_wkhtmltopdf_bin():
    return find_in_path('wkhtmltopdf')

class ProductSmallLabel(models.TransientModel):
    _name = "product.small.label"
   
   
#   Default Product Selection from Other forms
    @api.model
    def default_get(self, default_fields):
        res=super(ProductSmallLabel, self).default_get(default_fields)
        product_ids=[]
        total_qty=[]
        if self._context.get('active_model')=='sale.order':
            sale_ids=self.env['sale.order'].browse(self._context.get('active_ids'))
            if sale_ids:
                for sale in sale_ids:
                    if sale.order_line:
                        for line in sale.order_line:
                            if line.product_id.type=='service':
                                continue
                            total_qty.append({'product_id':line.product_id,'qty':line.product_uom_qty}) 
                            if line.product_id not in product_ids:
                                product_ids.append(line.product_id)
            for lines in total_qty:
                qty=0
                product=lines.get('product_id')
                for line in total_qty:
                    if product==line.get('product_id'):
                        qty=qty+line.get('qty')
                        product.write({'gt_quantity':qty})
            res['product_ids']=[(6,0,[product.id for product in product_ids])]
            return res
        elif self._context.get('active_model')=='purchase.order':
            sale_ids=self.env['purchase.order'].browse(self._context.get('active_ids'))
            if sale_ids:
                for sale in sale_ids:
                    if sale.order_line:
                        for line in sale.order_line:
                            if line.product_id.type=='service':
                                continue
                            total_qty.append({'product_id':line.product_id,'qty':line.product_qty}) 
                            if line.product_id not in product_ids:
                                product_ids.append(line.product_id)
            for lines in total_qty:
                qty=0
                product=lines.get('product_id')
                for line in total_qty:
                    if product==line.get('product_id'):
                        qty=qty+line.get('qty')
                        product.write({'gt_quantity':qty})
            res['product_ids']=[(6,0,[product.id for product in product_ids])]
            return res
        elif self._context.get('active_model')=='account.invoice':
            sale_ids=self.env['account.invoice'].browse(self._context.get('active_ids'))
            if sale_ids:
                for sale in sale_ids:
                    if sale.invoice_line_ids:
                        for line in sale.invoice_line_ids:
                            if line.product_id.type=='service':
                                continue
                            total_qty.append({'product_id':line.product_id,'qty':line.quantity}) 
                            if line.product_id not in product_ids:
                                product_ids.append(line.product_id)
            for lines in total_qty:
                qty=0
                product=lines.get('product_id')
                for line in total_qty:
                    if product==line.get('product_id'):
                        qty=qty+line.get('qty')
                        product.write({'gt_quantity':qty})
            res['product_ids']=[(6,0,[product.id for product in product_ids])]
            return res
        
        elif self._context.get('active_model')=='product.product':
            sale_ids=self.env['product.product'].browse(self._context.get('active_ids'))
            if sale_ids:
                for sale in sale_ids:
                    if sale.type=='service':
                        continue
                    product_ids.append(sale)
                    sale.write({'gt_quantity':1})
            res['product_ids']=[(6,0,[product.id for product in product_ids])]
            return res
        elif self._context.get('active_model')=='product.template':
            sale_ids=self.env['product.product'].search([('product_tmpl_id','in',(self._context.get('active_ids')))])
            if sale_ids:
                for sale in sale_ids:
                    if sale.type=='service':
                        continue
                    product_ids.append(sale)
                    sale.write({'gt_quantity':1})
            res['product_ids']=[(6,0,[product.id for product in product_ids])]
            return res
        elif self._context.get('active_model')=='stock.picking':
            sale_ids=self.env['stock.picking'].browse(self._context.get('active_ids'))
            if sale_ids:
                for sale in sale_ids:
                    if sale.move_ids_without_package:
                        for line in sale.move_ids_without_package:
                            if line.product_id.type=='service':
                                continue
                            total_qty.append({'product_id':line.product_id,'qty':line.product_uom_qty}) 
                            if line.product_id not in product_ids:
                                product_ids.append(line.product_id)
            for lines in total_qty:
                qty=0
                product=lines.get('product_id')
                for line in total_qty:
                    if product==line.get('product_id'):
                        qty=qty+line.get('qty')
                        product.write({'gt_quantity':qty})
            res['product_ids']=[(6,0,[product.id for product in product_ids])]
            return res
        else:
            return res
#   Make the model label.design Name Field as a selection field
    def _get_template(self):
        values=[]
        fields=self.env['label.design'].search([])
        for value in fields:
            values.append((str(value.id),str(value.name)))
        return values
    
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    template=fields.Selection(selection='_get_template')
    design_format=fields.Selection([('xml_design','XML Design'),('field_selection','Fields Selection')],default='xml_design',string="Design Using")
    update_template = fields.Boolean(string='Update Existing Template')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist',
        help="The pricelist used if no customer is selected or if the customer has no Sale Pricelist configured.")
#    attribute_ids=fields.Many2many('product.attribute.value','wizard_attribute_rel','wizard_id','attribute_id','Product Attributes')
    product_ids=fields.Many2many('product.product','wizard_product_rel','wizard_id','product_id','Product')
    
    label_width=fields.Float('Label Width (mm)',default="50")
    label_height=fields.Float('Label Height (mm)',default="50")
    top_margin=fields.Float('Margin Top (mm)')
    left_margin=fields.Float('Margin Left (mm)')
    bottom_margin=fields.Float('Margin Bottom (mm)')
    right_margin=fields.Float('Margin Right (mm)')
    dpi=fields.Integer('DPI',default="90")
    logo_label = fields.Binary(string="Label Logo")
    logo_position=fields.Selection([('top','Top'),('bottom','Bottom')],default='top',string="Logo Position")
    currency_position=fields.Selection([('before','Before'),('after','After')],default='before',string="Currency Position")
    logo_height=fields.Float(string="Logo Height(px)",default="50")
    logo_width=fields.Float(string="Logo Width(px)",default="100")
    
    barcode_width=fields.Float('Width',default="600")
    display_width=fields.Float('Display Width(px)',default="100")
    barcode_height=fields.Float('Height',default="20")
    display_height=fields.Float('Display Height(px)',default="20")
    barcode_type=fields.Selection([('EAN13','EAN13'),('Code128','Code128'),('EAN8','EAN8')],default='EAN13',string="Barcode Type")
    barcode=fields.Boolean(default=True)
    readable=fields.Boolean('HumanReadable')
    barcode_field = fields.Selection([('internal','Internal Reference'),('barcode','Barcode')],default='barcode',string="Barcode Field")
    
    field_ids = fields.Many2many('custom.report.fields','wizard_field_rel','wizard_id','field_id')
    
    
    @api.onchange('template')
    def _set_template_config(self):
        if self.template:
            label_id=self.env['label.design'].browse(int(self.template))
            if label_id.template_saved:
                self.pricelist_id=label_id.pricelist_id.id
                self.label_width=label_id.label_width
                self.label_height=label_id.label_height
                self.top_margin=label_id.top_margin
                self.left_margin=label_id.left_margin
                self.bottom_margin=label_id.bottom_margin
                self.right_margin=label_id.right_margin
                self.dpi=label_id.dpi
                self.logo_label=label_id.logo_label
                self.logo_position=label_id.logo_position
                self.currency_position=label_id.currency_position
                self.logo_height=label_id.logo_height
                self.logo_width=label_id.logo_width
                self.barcode_width=label_id.barcode_width
                self.display_width=label_id.display_width
                self.barcode_height=label_id.barcode_height
                self.display_height=label_id.display_height
                self.barcode_type=label_id.barcode_type
                self.barcode=label_id.barcode
                self.readable=label_id.readable
                self.barcode_field=label_id.barcode_field
                self.design_format=label_id.design_format
                self.field_ids=label_id.field_ids
            
    @api.multi
    def save_template(self):
        label_id=self.env['label.design'].browse(int(self.template))
#        it will check that this template is already saved or not if saved give warning to update
        if label_id.template_saved and not self.update_template:
            raise RedirectWarning(_('This template is already saved want to update.please select "Update Existing Template" option !'))
        elif label_id.default_design:
            raise RedirectWarning(_('You can not save template for Deafult Design.Please create custom template!'))
        else:
            label_id.write({'template_saved':True,'design_format':self.design_format,'field_ids':[(6,0,[x.id for x in self.field_ids])],'pricelist_id':self.pricelist_id.id,'label_width':self.label_width,'label_height':self.label_height,'top_margin':self.top_margin,'left_margin':self.left_margin,'bottom_margin':self.bottom_margin,'right_margin':self.right_margin,'dpi':self.dpi,'logo_label':self.logo_label,'logo_position':self.logo_position,'currency_position':self.currency_position,'logo_height':self.logo_height,'logo_width':self.logo_width,'barcode_width':self.barcode_width,'display_width':self.display_width,'barcode_height':self.barcode_height,'display_height':self.display_height,'barcode_type':self.barcode_type,'barcode':self.barcode,'readable':self.readable,'barcode_field':self.barcode_field})
    
    @api.multi
    def products_list(self):
        return self.product_ids
    
    @api.multi
    def get_style(self):
        return "width:"+str(self.display_width)+'px'+";""height:"+str(self.display_height)+'px'+";"
    
    @api.multi
    def get_logo_style(self):
        return "width:"+str(self.logo_width)+'px'+";""height:"+str(self.logo_height)+'px'+";"
    
    @api.multi
    def _pricelist_amount(self,amount):
        if self.pricelist_id:
            currency = self.pricelist_id.currency_id.with_context(date=fields.Date.today()) # Pricelist Currency
            company_currency = self.company_id.currency_id # Company Currency
            return company_currency.compute(amount, currency)  # From Invoice Currency, amount is converted to Company's Currency
        else:
            return amount

    @api.multi
    def print_report(self):
        if self.design_format=='field_selection':
            if not self.field_ids or not self.product_ids:
                raise RedirectWarning(_('Please select fields and products to continue.!'))
            else:
                pro_obj=self.env['product.product']
                template_middle=''
                top=''
                bottom=''
                left=''
                right=''
#                It will short fields by sequence wise
                for line in self.field_ids.sorted(lambda line:line.sequence):
                    template_unique=''
                    field_dict=pro_obj.fields_get(line.name)
                    field_name=field_dict.get(line.name)
                    field_type=field_name.get('type')
                    template_currency=''
                    template_barcode=''
                    margin_string=line.margin.split(',')
                    if len(margin_string)!=4:
                        raise RedirectWarning(_('Please select fields to continue.!'))
                    if line.currency:
                        if field_type=='float':
                            template_currency='<span>'+(self.pricelist_id.currency_id.symbol if self.pricelist_id else self.company_id.currency_id.symbol)+'</span>'
                    if field_type=='many2many' and line.name=='attribute_value_ids':
                        template_unique+='<t t-foreach="products.attribute_value_ids" t-as="attribute"><span t-field="attribute.attribute_id.name"/>:<span t-field="attribute.name"/>;</t>'
                    if field_type=='many2one':
                        template_unique+='<span t-field="products.'+line.name+'.name"/>'
                    if field_type not in('many2one','many2many','float'):
                        if line.name=='barcode' and self.barcode_field=='barcode' and self.barcode: 
                            template_unique+='<span/>'
                        elif line.name=='default_code' and self.barcode_field=='internal' and self.barcode:
                            template_unique+='<span/>'
                        else:
                            template_unique+='<span t-field="products.'+line.name+'"/>'
#                    assign the margins
                    top=margin_string[0]
                    bottom=margin_string[2]
                    left=margin_string[3]
                    right=margin_string[1]
                    if self.currency_position=='after':
                        if line.name=='default_code' and self.barcode_field=='internal' and self.barcode:
                            if self.barcode_type=='EAN13':
                                template_barcode='<t t-set="style" t-value="doc.get_style()"/><img alt="Barcode" t-att-style="style" t-att-src="'+"'"+'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s'"'"+' % ('"'"'EAN13'+"'"+', products.default_code,int(doc.barcode_width),int(doc.barcode_height))"'+'/>'
                            if self.barcode_type=='Code128':
                                template_barcode='<t t-set="style" t-value="doc.get_style()"/><img alt="Barcode" t-att-style="style" t-att-src="'+"'"+'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s'"'"+' % ('"'"'Code128'+"'"+', products.default_code,int(doc.barcode_width),int(doc.barcode_height))"'+'/>'
                            if self.barcode_type=='EAN8':
                                template_barcode='<t t-set="style" t-value="doc.get_style()"/><img alt="Barcode" t-att-style="style" t-att-src="'+"'"+'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s'"'"+' % ('"'"'EAN8'+"'"+', products.default_code,int(doc.barcode_width),int(doc.barcode_height))"'+'/>'
                            template_middle+='<div style="color:'+line.color.lower()+';font-size:'+str(line.size)+'px;width:'+str(line.width)+'%;margin-top:'+top+'%;margin-bottom:'+bottom+'%;margin-right:'+right+'%;margin-left:'+left+'%"'+'>'+template_barcode+'</div>'
                            if self.readable:
                                template_middle+='<div style="color:'+line.color.lower()+';font-size:'+str(line.size)+'px;width:'+str(line.width)+'%;margin-top:'+top+'%;margin-bottom:'+bottom+'%;margin-right:'+right+'%;margin-left:'+left+'%"'+'><span t-field="products.default_code"/></div>'
                        elif line.name=='barcode' and self.barcode_field=='barcode' and self.barcode:
                            if self.barcode_type=='EAN13':
                                template_barcode='<t t-set="style" t-value="doc.get_style()"/><img alt="Barcode" t-att-style="style" t-att-src="'+"'"+'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s'"'"+' % ('"'"'EAN13'+"'"+', products.barcode,int(doc.barcode_width),int(doc.barcode_height))"'+'/>'
                            if self.barcode_type=='Code128':
                                template_barcode='<t t-set="style" t-value="doc.get_style()"/><img alt="Barcode" t-att-style="style" t-att-src="'+"'"+'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s'"'"+' % ('"'"'Code128'+"'"+', products.barcode,int(doc.barcode_width),int(doc.barcode_height))"'+'/>'
                            if self.barcode_type=='EAN8':
                                template_barcode='<t t-set="style" t-value="doc.get_style()"/><img alt="Barcode" t-att-style="style" t-att-src="'+"'"+'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s'"'"+' % ('"'"'EAN8'+"'"+', products.barcode,int(doc.barcode_width),int(doc.barcode_height))"'+'/>'
                            template_middle+='<div style="color:'+line.color.lower()+';font-size:'+str(line.size)+'px;width:'+str(line.width)+'%;margin-top:'+top+'%;margin-bottom:'+bottom+'%;margin-right:'+right+'%;margin-left:'+left+'%"'+'>'+template_barcode+'</div>'
                            if self.readable:
                                template_middle+='<div style="color:'+line.color.lower()+';font-size:'+str(line.size)+'px;width:'+str(line.width)+'%;margin-top:'+top+'%;margin-bottom:'+bottom+'%;margin-right:'+right+'%;margin-left:'+left+'%"'+'><span t-field="products.barcode"/></div>'
                        elif field_type=='float':
                            template_middle+='<div style="color:'+line.color.lower()+';font-size:'+str(line.size)+'px;width:'+str(line.width)+'%;margin-top:'+top+'%;margin-bottom:'+bottom+'%;margin-right:'+right+'%;margin-left:'+left+'%"'+'><span t-esc="'+"'%.2f'"+'%(doc._pricelist_amount(products.'+line.name+'))"/> '+template_currency+'</div>'
                        else:
                            template_middle+='<div style="color:'+line.color.lower()+';font-size:'+str(line.size)+'px;width:'+str(line.width)+'%;margin-top:'+top+'%;margin-bottom:'+bottom+'%;margin-right:'+right+'%;margin-left:'+left+'%"'+'>'+template_unique+'</div>'
                            
                    if self.currency_position=='before':
                        
                        if line.name=='default_code' and self.barcode_field=='internal' and self.barcode:
                            if self.barcode_type=='EAN13':
                                
                                template_barcode='<t t-set="style" t-value="doc.get_style()"/><img alt="Barcode" t-att-style="style" t-att-src="'+"'"+'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s'"'"+' % ('"'"'EAN13'+"'"+', products.default_code,int(doc.barcode_width),int(doc.barcode_height))"'+'/>'
                            if self.barcode_type=='Code128':
                               
                                template_barcode='<t t-set="style" t-value="doc.get_style()"/><img alt="Barcode" t-att-style="style" t-att-src="'+"'"+'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s'"'"+' % ('"'"'Code128'+"'"+', products.default_code,int(doc.barcode_width),int(doc.barcode_height))"'+'/>'
                            if self.barcode_type=='EAN8':
                                
                                template_barcode='<t t-set="style" t-value="doc.get_style()"/><img alt="Barcode" t-att-style="style" t-att-src="'+"'"+'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s'"'"+' % ('"'"'EAN8'+"'"+', products.default_code,int(doc.barcode_width),int(doc.barcode_height))"'+'/>'
                            template_middle+='<div style="color:'+line.color.lower()+';font-size:'+str(line.size)+'px;width:'+str(line.width)+'%;margin-top:'+top+'%;margin-bottom:'+bottom+'%;margin-right:'+right+'%;margin-left:'+left+'%"'+'>'+template_barcode+'</div>'
                            if self.readable:
                                template_middle+='<div style="color:'+line.color.lower()+';font-size:'+str(line.size)+'px;width:'+str(line.width)+'%;margin-top:'+top+'%;margin-bottom:'+bottom+'%;margin-right:'+right+'%;margin-left:'+left+'%"'+'><span t-field="products.default_code"/></div>'
                        elif line.name=='barcode' and self.barcode_field=='barcode' and self.barcode:
                            if self.barcode_type=='EAN13':
                                template_barcode='<t t-set="style" t-value="doc.get_style()"/><img alt="Barcode" t-att-style="style" t-att-src="'+"'"+'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s'"'"+' % ('"'"'EAN13'+"'"+', products.barcode,int(doc.barcode_width),int(doc.barcode_height))"'+'/>'
                            if self.barcode_type=='Code128':
                                template_barcode='<t t-set="style" t-value="doc.get_style()"/><img alt="Barcode" t-att-style="style" t-att-src="'+"'"+'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s'"'"+' % ('"'"'Code128'+"'"+', products.barcode,int(doc.barcode_width),int(doc.barcode_height))"'+'/>'
                            if self.barcode_type=='EAN8':
                                template_barcode='<t t-set="style" t-value="doc.get_style()"/><img alt="Barcode" t-att-style="style" t-att-src="'+"'"+'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s'"'"+' % ('"'"'EAN8'+"'"+', products.barcode,int(doc.barcode_width),int(doc.barcode_height))"'+'/>'
                            template_middle+='<div style="color:'+line.color.lower()+';font-size:'+str(line.size)+'px;width:'+str(line.width)+'%;margin-top:'+top+'%;margin-bottom:'+bottom+'%;margin-right:'+right+'%;margin-left:'+left+'%"'+'>'+template_barcode+'</div>'
                            if self.readable:
                                template_middle+='<div style="color:'+line.color.lower()+';font-size:'+str(line.size)+'px;width:'+str(line.width)+'%;margin-top:'+top+'%;margin-bottom:'+bottom+'%;margin-right:'+right+'%;margin-left:'+left+'%"'+'><span t-field="products.barcode"/></div>'
                        elif field_type=='float':
                            template_middle+='<div style="color:'+line.color.lower()+';font-size:'+str(line.size)+'px;width:'+str(line.width)+'%;margin-top:'+top+'%;margin-bottom:'+bottom+'%;margin-right:'+right+'%;margin-left:'+left+'%"'+'> '+template_currency+' <span t-esc="'+"'%.2f'"+'%(doc._pricelist_amount(products.'+line.name+'))"/></div>'
                        else:
                            template_middle+='<div style="color:'+line.color.lower()+';font-size:'+str(line.size)+'px;width:'+str(line.width)+'%;margin-top:'+top+'%;margin-bottom:'+bottom+'%;margin-right:'+right+'%;margin-left:'+left+'%"'+'>'+template_unique+'</div>'
                    if not self.currency_position:
                        if line.name=='default_code' and self.barcode_field=='internal' and self.barcode:
                            if self.barcode_type=='EAN13':
                                template_barcode='<t t-set="style" t-value="doc.get_style()"/><img alt="Barcode" t-att-style="style" t-att-src="'+"'"+'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s'"'"+' % ('"'"'EAN13'+"'"+', products.default_code,int(doc.barcode_width),int(doc.barcode_height))"'+'/>'
                            if self.barcode_type=='Code128':
                                template_barcode='<t t-set="style" t-value="doc.get_style()"/><img alt="Barcode" t-att-style="style" t-att-src="'+"'"+'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s'"'"+' % ('"'"'Code128'+"'"+', products.default_code,int(doc.barcode_width),int(doc.barcode_height))"'+'/>'
                            if self.barcode_type=='EAN8':
                                template_barcode='<t t-set="style" t-value="doc.get_style()"/><img alt="Barcode" t-att-style="style" t-att-src="'+"'"+'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s'"'"+' % ('"'"'EAN8'+"'"+', products.default_code,int(doc.barcode_width),int(doc.barcode_height))"'+'/>'
                            template_middle+='<div style="color:'+line.color.lower()+';font-size:'+str(line.size)+'px;width:'+str(line.width)+'%;margin-top:'+top+'%;margin-bottom:'+bottom+'%;margin-right:'+right+'%;margin-left:'+left+'%"'+'>'+template_barcode+'</div>'
                            if self.readable:
                                template_middle+='<div style="color:'+line.color.lower()+';font-size:'+str(line.size)+'px;width:'+str(line.width)+'%;margin-top:'+top+'%;margin-bottom:'+bottom+'%;margin-right:'+right+'%;margin-left:'+left+'%"'+'><span t-field="products.default_code"/></div>'
                        elif line.name=='barcode' and self.barcode_field=='barcode' and self.barcode:
                            if self.barcode_type=='EAN13':
                                template_barcode='<t t-set="style" t-value="doc.get_style()"/><img alt="Barcode" t-att-style="style" t-att-src="'+"'"+'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s'"'"+' % ('"'"'EAN13'+"'"+', products.barcode,int(doc.barcode_width),int(doc.barcode_height))"'+'/>'
                            if self.barcode_type=='Code128':
                                template_barcode='<t t-set="style" t-value="doc.get_style()"/><img alt="Barcode" t-att-style="style" t-att-src="'+"'"+'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s'"'"+' % ('"'"'Code128'+"'"+', products.barcode,int(doc.barcode_width),int(doc.barcode_height))"'+'/>'
                            if self.barcode_type=='EAN8':
                                template_barcode='<t t-set="style" t-value="doc.get_style()"/><img alt="Barcode" t-att-style="style" t-att-src="'+"'"+'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s'"'"+' % ('"'"'EAN8'+"'"+', products.barcode,int(doc.barcode_width),int(doc.barcode_height))"'+'/>'
                            template_middle+='<div style="color:'+line.color.lower()+';font-size:'+str(line.size)+'px;width:'+str(line.width)+'%;margin-top:'+top+'%;margin-bottom:'+bottom+'%;margin-right:'+right+'%;margin-left:'+left+'%"'+'>'+template_barcode+'</div>'
                            if self.readable:
                                template_middle+='<div style="color:'+line.color.lower()+';font-size:'+str(line.size)+'px;width:'+str(line.width)+'%;margin-top:'+top+'%;margin-bottom:'+bottom+'%;margin-right:'+right+'%;margin-left:'+left+'%"'+'><span t-field="products.barcode"/></div>'
                        elif field_type=='float':
                            template_middle+='<div style="color:'+line.color.lower()+';font-size:'+str(line.size)+'px;width:'+str(line.width)+'%;margin-top:'+top+'%;margin-bottom:'+bottom+'%;margin-right:'+right+'%;margin-left:'+left+'%"'+'><span t-esc="'+"'%.2f'"+'%(doc._pricelist_amount(products.'+line.name+'))"/></div>'
                        else:
                            template_middle+='<div style="color:'+line.color.lower()+';font-size:'+str(line.size)+'px;width:'+str(line.width)+'%;margin-top:'+top+'%;margin-bottom:'+bottom+'%;margin-right:'+right+'%;margin-left:'+left+'%"'+'>'+template_unique+'</div>'

                view_obj=self.env['ir.ui.view']
#                Prepare the template for creating xml template
                main_template = '''<?xml version="1.0"?>
                        <t t-name="gt_dynamic_product_small_label.label_report_template_fields">
                            <t t-call="web.html_container">
                                <t t-foreach="docs" t-as="doc">
                                    <t t-foreach="doc.products_list()" t-as="products">
                                        <t t-foreach="products.gt_quantity" t-as="product">
                                            <t t-call="web.basic_layout">
                                                <div class="page">
                                                <t t-if="doc.logo_position=='top'">
                                                    <t t-if="doc.logo_label">
                                                        <t t-set="logo_style" t-value="doc.get_logo_style()"/>
                                                            <div align="center">
                                                                <img t-att-src="image_data_uri(doc.logo_label)" alt="Logo" t-att-style="logo_style"/>
                                                            </div>
                                                        </t>
                                                    </t>'''
                                                   
                main_template+=template_middle
                template_bottom='''         
                                            <t t-if="doc.logo_position=='bottom'">
                                                    <t t-if="doc.logo_label">
                                                        <t t-set="logo_style" t-value="doc.get_logo_style()"/>
                                                        <div align="center">
                                                            <img t-att-src="image_data_uri(doc.logo_label)" alt="Logo" t-att-style="logo_style"/>
                                                        </div>
                                                    </t>
                                                </t>
                                            </div>
                                        </t>
                                    </t>
                                </t>
                            </t>
                        </t>
                    </t>
                                                    '''
                main_template+=template_bottom
#                Serach for the exesting template
                exists_view_id=view_obj.search([('name','=','label_report_template_fields')])
#                If not found create otherwise update
                if not exists_view_id:
#                Creates ir.mode.data 
                    data_vals={
                            'module':'gt_dynamic_product_small_label',
                            'name':'label_report_template_fields',
                            'display_name':'label_report_template_fields',
                            'model':'ir.ui.view',
                            'reference':'label_report_template_fields',
                            }
                    model_data_id=self.env['ir.model.data'].create(data_vals)
#                Create xml template view for field selection
                    view_vals={
                        'name':'label_report_template_fields',
                        'type':'qweb',
                        'inherit_id':False,
                        'priority':17,
                        'mode':'primary',
                        'model_data_id':model_data_id.id,
                        'arch_base':main_template.encode('utf-8'),
                        'xml_id':'gt_dynamic_product_small_label.label_report_template_fields',
                        }
#                    Create the view
                    view_id=view_obj.create(view_vals)
                    model_data_id.write({'res_id':view_id.id})
    #                Prepare the report data for creation
                    report_val={
                        'name':'Dynamic Product Label Field Selection',
                        'report_type':'qweb-pdf',
                        'model':'product.small.label',
                        'paperformat_id':self.env.ref('gt_dynamic_product_small_label.small_label_print_format').id,
                        'report_name':'gt_dynamic_product_small_label.label_report_template_fields',
                        }
                    report_id=self.env['ir.actions.report'].create(report_val)
                    return report_id.report_action(self)
                else:
                    exists_view_id.write({'arch_base':main_template.encode('utf-8')})
                    report_id=self.env['ir.actions.report'].search([('name','=','Dynamic Product Label Field Selection'),('paperformat_id','=',self.env.ref('gt_dynamic_product_small_label.small_label_print_format').id)],limit=1)
                    return report_id.report_action(self)
        else:
            if not self.product_ids:
                raise RedirectWarning(_('Please select products to continue.!'))
            return self.env.ref('gt_dynamic_product_small_label.gt_print_label_report').report_action(self)

class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'
    
    @api.model
    def _build_wkhtmltopdf_args(
            self,
            paperformat_id,
            landscape,
            specific_paperformat_args=None,
            set_viewport_size=False):
        '''Build arguments understandable by wkhtmltopdf bin.

        :param paperformat_id: A report.paperformat record.
        :param landscape: Force the report orientation to be landscape.
        :param specific_paperformat_args: A dictionary containing prioritized wkhtmltopdf arguments.
        :param set_viewport_size: Enable a viewport sized '1024x1280' or '1280x1024' depending of landscape arg.
        :return: A list of string representing the wkhtmltopdf process command args.
        '''
        

        if landscape is None and specific_paperformat_args and specific_paperformat_args.get('data-report-landscape'):
            landscape = specific_paperformat_args.get('data-report-landscape')

        command_args = ['--disable-local-file-access']
        if set_viewport_size:
            command_args.extend(['--viewport-size', landscape and '1024x1280' or '1280x1024'])

        # Passing the cookie to wkhtmltopdf in order to resolve internal links.
        try:
            if request:
                command_args.extend(['--cookie', 'session_id', request.session.sid])
        except AttributeError:
            pass

        # Less verbose error messages
        command_args.extend(['--quiet'])
        # Build paperformat args
        if self.model=='product.small.label':
            label_model_id=self.env[self.model].browse(self._context.get('res_id'))
            if paperformat_id:
                if paperformat_id.format and paperformat_id.format != 'custom':
                    command_args.extend(['--page-size', paperformat_id.format])

                if paperformat_id.page_height and paperformat_id.page_width and paperformat_id.format == 'custom':
                    command_args.extend(['--page-width', str(label_model_id.label_width) + 'mm'])
                    command_args.extend(['--page-height', str(label_model_id.label_height) + 'mm'])

                if specific_paperformat_args and specific_paperformat_args.get('data-report-margin-top'):
                    command_args.extend(['--margin-top', str(specific_paperformat_args['data-report-margin-top'])])
                else:
                    command_args.extend(['--margin-top', str(label_model_id.top_margin)])

                if specific_paperformat_args and specific_paperformat_args.get('data-report-dpi'):
                    command_args.extend(['--dpi', str(specific_paperformat_args['data-report-dpi'])])
                elif paperformat_id.dpi:
                    if os.name == 'nt' and int(label_model_id.dpi) <= 95:
                        _logger.info("Generating PDF on Windows platform require DPI >= 96. Using 96 instead.")
                        command_args.extend(['--dpi', '96'])
                    else:
                        command_args.extend(['--dpi', str(label_model_id.dpi)])

                if specific_paperformat_args and specific_paperformat_args.get('data-report-header-spacing'):
                    command_args.extend(['--header-spacing', str(specific_paperformat_args['data-report-header-spacing'])])
                elif paperformat_id.header_spacing:
                    command_args.extend(['--header-spacing', str(paperformat_id.header_spacing)])

                command_args.extend(['--margin-left', str(label_model_id.left_margin)])
                command_args.extend(['--margin-bottom', str(label_model_id.bottom_margin)])
                command_args.extend(['--margin-right', str(label_model_id.right_margin)])
                if not landscape and paperformat_id.orientation:
                    command_args.extend(['--orientation', str(paperformat_id.orientation)])
                if paperformat_id.header_line:
                    command_args.extend(['--header-line'])
        else:
            if paperformat_id:
                if paperformat_id.format and paperformat_id.format != 'custom':
                    command_args.extend(['--page-size', paperformat_id.format])

                if paperformat_id.page_height and paperformat_id.page_width and paperformat_id.format == 'custom':
                    command_args.extend(['--page-width', str(paperformat_id.page_width) + 'mm'])
                    command_args.extend(['--page-height', str(paperformat_id.page_height) + 'mm'])

                if specific_paperformat_args and specific_paperformat_args.get('data-report-margin-top'):
                    command_args.extend(['--margin-top', str(specific_paperformat_args['data-report-margin-top'])])
                else:
                    command_args.extend(['--margin-top', str(paperformat_id.margin_top)])

                if specific_paperformat_args and specific_paperformat_args.get('data-report-dpi'):
                    command_args.extend(['--dpi', str(specific_paperformat_args['data-report-dpi'])])
                elif paperformat_id.dpi:
                    if os.name == 'nt' and int(paperformat_id.dpi) <= 95:
                        _logger.info("Generating PDF on Windows platform require DPI >= 96. Using 96 instead.")
                        command_args.extend(['--dpi', '96'])
                    else:
                        command_args.extend(['--dpi', str(paperformat_id.dpi)])

                if specific_paperformat_args and specific_paperformat_args.get('data-report-header-spacing'):
                    command_args.extend(['--header-spacing', str(specific_paperformat_args['data-report-header-spacing'])])
                elif paperformat_id.header_spacing:
                    command_args.extend(['--header-spacing', str(paperformat_id.header_spacing)])

                command_args.extend(['--margin-left', str(paperformat_id.margin_left)])
                command_args.extend(['--margin-bottom', str(paperformat_id.margin_bottom)])
                command_args.extend(['--margin-right', str(paperformat_id.margin_right)])
                if not landscape and paperformat_id.orientation:
                    command_args.extend(['--orientation', str(paperformat_id.orientation)])
                if paperformat_id.header_line:
                    command_args.extend(['--header-line'])
        if landscape:
            command_args.extend(['--orientation', 'landscape'])

        return command_args
    
    @api.model
    def _run_wkhtmltopdf(
            self,
            bodies,
            header=None,
            footer=None,
            landscape=False,
            specific_paperformat_args=None,
            set_viewport_size=False):
        '''Execute wkhtmltopdf as a subprocess in order to convert html given in input into a pdf
        document.

        :param bodies: The html bodies of the report, one per page.
        :param header: The html header of the report containing all headers.
        :param footer: The html footer of the report containing all footers.
        :param landscape: Force the pdf to be rendered under a landscape format.
        :param specific_paperformat_args: dict of prioritized paperformat arguments.
        :param set_viewport_size: Enable a viewport sized '1024x1280' or '1280x1024' depending of landscape arg.
        :return: Content of the pdf as a string
        '''
        paperformat_id = self.get_paperformat()
        
        
        # Build the base command args for wkhtmltopdf bin
#        Customized Code
        if self.model=='product.small.label':
            paperformat_id=self.env.ref('gt_dynamic_product_small_label.small_label_print_format')
            command_args = self.with_context(self._context)._build_wkhtmltopdf_args(
                paperformat_id,
                landscape,
                specific_paperformat_args=specific_paperformat_args,
                set_viewport_size=set_viewport_size)
        else:
            command_args = self._build_wkhtmltopdf_args(
               paperformat_id,
               landscape,
               specific_paperformat_args=specific_paperformat_args,
               set_viewport_size=set_viewport_size)
               
        files_command_args = []
        temporary_files = []
        if header:
            head_file_fd, head_file_path = tempfile.mkstemp(suffix='.html', prefix='report.header.tmp.')
            with closing(os.fdopen(head_file_fd, 'wb')) as head_file:
                head_file.write(header)
            temporary_files.append(head_file_path)
            files_command_args.extend(['--header-html', head_file_path])
        if footer:
            foot_file_fd, foot_file_path = tempfile.mkstemp(suffix='.html', prefix='report.footer.tmp.')
            with closing(os.fdopen(foot_file_fd, 'wb')) as foot_file:
                foot_file.write(footer)
            temporary_files.append(foot_file_path)
            files_command_args.extend(['--footer-html', foot_file_path])

        paths = []
        for i, body in enumerate(bodies):
            prefix = '%s%d.' % ('report.body.tmp.', i)
            body_file_fd, body_file_path = tempfile.mkstemp(suffix='.html', prefix=prefix)
            with closing(os.fdopen(body_file_fd, 'wb')) as body_file:
                body_file.write(body)
            paths.append(body_file_path)
            temporary_files.append(body_file_path)

        pdf_report_fd, pdf_report_path = tempfile.mkstemp(suffix='.pdf', prefix='report.tmp.')
        os.close(pdf_report_fd)
        temporary_files.append(pdf_report_path)

        try:
            wkhtmltopdf = [_get_wkhtmltopdf_bin()] + command_args + files_command_args + paths + [pdf_report_path]
            process = subprocess.Popen(wkhtmltopdf, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = process.communicate()

            if process.returncode not in [0, 1]:
                if process.returncode == -11:
                    message = _(
                        'Wkhtmltopdf failed (error code: %s). Memory limit too low or maximum file number of subprocess reached. Message : %s')
                else:
                    message = _('Wkhtmltopdf failed (error code: %s). Message: %s')
                raise UserError(message % (str(process.returncode), err[-1000:]))
            else:
                if err:
                    _logger.warning('wkhtmltopdf: %s' % err)
        except:
            raise

        with open(pdf_report_path, 'rb') as pdf_document:
            pdf_content = pdf_document.read()

        # Manual cleanup of the temporary files
        for temporary_file in temporary_files:
            try:
                os.unlink(temporary_file)
            except (OSError, IOError):
                _logger.error('Error when trying to remove file %s' % temporary_file)

        return pdf_content
    
    @api.multi
    def render_qweb_pdf(self, res_ids=None, data=None):
        if not data:
            data = {}

        # remove editor feature in pdf generation
        data.update(enable_editor=False)

        # In case of test environment without enough workers to perform calls to wkhtmltopdf,
        # fallback to render_html.
        if tools.config['test_enable']:
            return self.render_qweb_html(res_ids, data=data)

        # As the assets are generated during the same transaction as the rendering of the
        # templates calling them, there is a scenario where the assets are unreachable: when
        # you make a request to read the assets while the transaction creating them is not done.
        # Indeed, when you make an asset request, the controller has to read the `ir.attachment`
        # table.
        # This scenario happens when you want to print a PDF report for the first time, as the
        # assets are not in cache and must be generated. To workaround this issue, we manually
        # commit the writes in the `ir.attachment` table. It is done thanks to a key in the context.
        context = dict(self.env.context)
        if not config['test_enable']:
            context['commit_assetsbundle'] = True

        # Disable the debug mode in the PDF rendering in order to not split the assets bundle
        # into separated files to load. This is done because of an issue in wkhtmltopdf
        # failing to load the CSS/Javascript resources in time.
        # Without this, the header/footer of the reports randomly disapear
        # because the resources files are not loaded in time.
        # https://github.com/wkhtmltopdf/wkhtmltopdf/issues/2083
        context['debug'] = False

        # The test cursor prevents the use of another environnment while the current
        # transaction is not finished, leading to a deadlock when the report requests
        # an asset bundle during the execution of test scenarios. In this case, return
        # the html version.
        if isinstance(self.env.cr, TestCursor):
            return self.with_context(context).render_qweb_html(res_ids, data=data)[0]

        save_in_attachment = {}
        if res_ids:
            # Dispatch the records by ones having an attachment and ones requesting a call to
            # wkhtmltopdf.
            Model = self.env[self.model]
            record_ids = Model.browse(res_ids)
            wk_record_ids = Model
            if self.attachment:
                for record_id in record_ids:
                    attachment_id = self.retrieve_attachment(record_id)
                    if attachment_id:
                        save_in_attachment[record_id.id] = attachment_id
                    if not self.attachment_use or not attachment_id:
                        wk_record_ids += record_id
            else:
                wk_record_ids = record_ids
            res_ids = wk_record_ids.ids

        # A call to wkhtmltopdf is mandatory in 2 cases:
        # - The report is not linked to a record.
        # - The report is not fully present in attachments.
        if save_in_attachment and not res_ids:
            _logger.info('The PDF report has been generated from attachments.')
            return self._post_pdf(save_in_attachment), 'pdf'

        if self.get_wkhtmltopdf_state() == 'install':
            # wkhtmltopdf is not installed
            # the call should be catched before (cf /report/check_wkhtmltopdf) but
            # if get_pdf is called manually (email template), the check could be
            # bypassed
            raise UserError(_("Unable to find Wkhtmltopdf on this system. The PDF can not be created."))

        html = self.with_context(context).render_qweb_html(res_ids, data=data)[0]

        # Ensure the current document is utf-8 encoded.
        html = html.decode('utf-8')

        bodies, html_ids, header, footer, specific_paperformat_args = self.with_context(context)._prepare_html(html)

        if self.attachment and set(res_ids) != set(html_ids):
            raise UserError(_("The report's template '%s' is wrong, please contact your administrator. \n\n"
                "Can not separate file to save as attachment because the report's template does not contains the attributes 'data-oe-model' and 'data-oe-id' on the div with 'article' classname.") %  self.name)
        #        Customized Code
        if self.model=='product.small.label':
            context=self._context.copy()
            context.update({'res_id':res_ids})
            pdf_content = self.with_context(context)._run_wkhtmltopdf(
                bodies,
                header=header,
                footer=footer,
                landscape=context.get('landscape'),
                specific_paperformat_args=specific_paperformat_args,
                set_viewport_size=context.get('set_viewport_size'),
            )
        else:
            pdf_content = self._run_wkhtmltopdf(
                bodies,
                header=header,
                footer=footer,
                landscape=context.get('landscape'),
                specific_paperformat_args=specific_paperformat_args,
                set_viewport_size=context.get('set_viewport_size'),
            )

        if res_ids:
            _logger.info('The PDF report has been generated for records %s.' % (str(res_ids)))
            return self._post_pdf(save_in_attachment, pdf_content=pdf_content, res_ids=html_ids), 'pdf'
        return pdf_content, 'pdf'
    
    
    

    
    
