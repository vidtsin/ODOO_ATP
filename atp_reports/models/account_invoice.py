# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    incoterm_location = fields.Char(string="Incoterm Location", readonly=True,
                                    states={'draft': [('readonly', False)]})
    expedition_mode = fields.Char(string="Expedition Mode", readonly=True,
                                  states={'draft': [('readonly', False)]})
    is_tax_total = fields.Boolean(string="Tax Total", copy=False, default=False, readonly=True,
                                  states={'draft': [('readonly', False)]})
    is_cicr_ref_print = fields.Boolean(string="Print CICR Reference", copy=False, default=False, readonly=True,
                                       states={'draft': [('readonly', False)]})
    print_weight = fields.Boolean(string="Print Weight", default=True, readonly=False)