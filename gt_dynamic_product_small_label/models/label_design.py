# -*- coding: utf-8 -*-
#############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import api, models, fields, _

class LabelDesign(models.Model):
    _name = 'label.design'
    
    default_design=fields.Boolean()
    name = fields.Char('Name')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist',
        help="The pricelist used if no customer is selected or if the customer has no Sale Pricelist configured.")
    design_format=fields.Selection([('xml_design','XML Design'),('field_selection','Fields Selection')],string="Design Using")
    label_width=fields.Float('Label Width (mm)')
    label_height=fields.Float('Label Height (mm)')
    top_margin=fields.Float('Margin Top (mm)')
    left_margin=fields.Float('Margin Left (mm)')
    bottom_margin=fields.Float('Margin Bottom (mm)')
    right_margin=fields.Float('Margin Right (mm)')
    dpi=fields.Integer('DPI')
    logo_label = fields.Binary(string="Label Logo")
    logo_position=fields.Selection([('top','Top'),('bottom','Bottom')],string="Logo Position")
    currency_position=fields.Selection([('before','Before'),('after','After')],string="Currency Position")
    logo_height=fields.Float(string="Logo Height(px)")
    logo_width=fields.Float(string="Logo Width(px)")
    
    barcode_width=fields.Float('Width')
    display_width=fields.Float('Display Width(px)')
    barcode_height=fields.Float('Height')
    display_height=fields.Float('Display Height(px)')
    barcode_type=fields.Selection([('EAN13','EAN13'),('Code128','Code128'),('EAN8','EAN8')],string="Barcode Type")
    barcode=fields.Boolean()
    template_saved=fields.Boolean()
    readable=fields.Boolean('HumanReadable')
    barcode_field = fields.Selection([('internal','Internal Reference'),('barcode','Barcode')],string="Barcode Field")
    
    field_ids = fields.Many2many('custom.report.fields','label_design_field_rel','label_id','field_id')

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    gt_quantity=fields.Integer('Quantity')
    
class CustomReportFields(models.Model):
    _name='custom.report.fields'
    
    def _get_fields(self):
        fields=self.env['product.product'].fields_get()
        return [(k, v['string']) for k, v in fields.items()]
            
        
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)  
    size=fields.Integer('Font Size(px)',default='10')
    width=fields.Integer('Field Width(%)',default='100')
    color=fields.Char('Font Color',default='Black')
    margin=fields.Char('Field Margin(%)(T,R,B,L)',default='0,0,0,0')
    currency=fields.Boolean('With currency')
    sequence=fields.Integer('Sequence',default=1)
    name=fields.Selection(selection='_get_fields',string='Fields Name',default='default_code',required=True)