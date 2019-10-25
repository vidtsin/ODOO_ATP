# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    company_reg = fields.Char("Company Registration")
    annual_sales = fields.Char("Annual Sales")
    over_18 = fields.Boolean("Over 18")
