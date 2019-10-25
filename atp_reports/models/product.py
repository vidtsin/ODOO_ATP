# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    is_ce_print = fields.Boolean(string="CE")
    is_swissmade_print = fields.Boolean(string="Swissmade")
 