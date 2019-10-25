# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends('order_line.currency2_price_total')
    def _currency2_amount_all(self):
        """
        Compute the total amounts of the SO for second currency.
        """
        for order in self:
            if order.currency_id2:
                amount_untaxed = amount_tax = 0.0
                for line in order.order_line:
                    amount_untaxed += line.currency2_price_subtotal
                    amount_tax += line.currency2_price_tax
                order.update({
                    'currency2_amount_untaxed': order.currency_id2.round(amount_untaxed),
                    'currency2_amount_tax': order.currency_id2.round(amount_tax),
                    'currency2_amount_total': amount_untaxed + amount_tax,
                })

    currency2_amount_untaxed = fields.Float(string='Second Currency Untaxed Amount', store=True,
                                    readonly=True, compute='_currency2_amount_all')
    currency2_amount_tax = fields.Float(string='Second Currency Taxes', store=True,
                                    readonly=True, compute='_currency2_amount_all')
    currency2_amount_total = fields.Float(string='Second Currency Total', store=True,
                                    readonly=True, compute='_currency2_amount_all')
    incoterm_location = fields.Char(string="Incoterm Location", readonly=True,
                                    states={'draft': [('readonly', False)]})
    expedition_mode = fields.Char(string="Expedition Mode", readonly=True,
                                  states={'draft': [('readonly', False)]})
    is_tax_total = fields.Boolean(string="Tax Total", copy=False, default=False, readonly=True,
                                  states={'draft': [('readonly', False)]})
    is_cr_grouping = fields.Boolean(string="CR Grouping", copy=False, default=False, readonly=True,
                                    states={'draft': [('readonly', False)]})
    currency_id2 = fields.Many2one("res.currency", string="Second Currency", readonly=True,
                                   states={'draft': [('readonly', False)]})
    currency2_rate = fields.Float(string="Second Currency Rate", default=1.0, readonly=True,
                                  states={'draft': [('readonly', False)]})
    pro_forma_number = fields.Char(string="Pro-Forma Number", copy=False, readonly=True,
                                   states={'draft': [('readonly', False)]})
    is_cicr_ref_print = fields.Boolean(string="Print CICR Reference", default=False, readonly=True,
                                       states={'draft': [('readonly', False)]})
    
    print_weight = fields.Boolean(string="Print Weight", default=True, readonly=False)

    @api.multi
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.update({
            'incoterm_location': self.incoterm_location,
            'expedition_mode': self.expedition_mode,
            'is_tax_total': self.is_tax_total,
            'is_cr_grouping': self.is_cr_grouping,
            'currency_id2': self.currency_id2.id,
            'currency2_rate': self.currency2_rate,
            'is_cicr_ref_print': self.is_cicr_ref_print
        })
        return invoice_vals

    @api.multi
    def _get_currency2_bank_details(self):
        """
        Return second currency bank details
        """
        self.ensure_one()
        return self.env['res.partner.bank'].search([('division_id', '=', self.division_id.id),
                                                    ('currency_id', '=', self.currency_id2.id),
                                                    ('company_id', '=', self.company_id.id),
                                                    ('partner_id', '=', self.company_id.partner_id.id)], limit=1)

    @api.multi
    def _get_proforma_invoice_line_groups(self):
        """
        Returns invoice line groups with total price
        """
        self.ensure_one()
        result = []
        group_lines = self.order_line.filtered(lambda line: line.product_id.invoice_line_group_id)
        for line in group_lines:
            group_id = line.product_id.invoice_line_group_id
            group_ids = [group[0] if group else 0 for group in result]
            if group_id.id not in group_ids:
                result.append([group_id.id, group_id.name, line.price_total])
            elif group_id.id in group_ids:
                for i in range(len(result)):
                    if result[i][0] == group_id.id:
                        result[i][2] = (result[i][2] + line.price_total)
        return result

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_uom_qty', 'discount', 'currency2_price_unit', 'tax_id')
    def _compute_currency2_amount(self):
        """
        Compute the amounts of the SO line for second currency.
        """
        for line in self:
            if line.order_id.currency_id2:
                price = line.currency2_price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_id.compute_all(price, line.order_id.currency_id2, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
                line.update({
                    'currency2_price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                    'currency2_price_total': taxes['total_included'],
                    'currency2_price_subtotal': taxes['total_excluded'],
                })

    @api.depends('product_uom_qty', 'price_unit', 'discount', 'order_id.currency_id2', 'order_id.currency2_rate')
    def _compute_currency2_price_unit(self):
        """
        Compute second currency price unit (price unit * second currency rate)
        """
        for line in self:
            if line.order_id.currency_id2 and line.order_id.currency2_rate:
                line.update({'currency2_price_unit': line.price_unit * line.order_id.currency2_rate})

    currency2_price_unit = fields.Float('Second Currency Unit Price', compute='_compute_currency2_price_unit', store=True)
    currency2_price_subtotal = fields.Float(compute='_compute_currency2_amount', string='Second Currency Subtotal', readonly=True, store=True)
    currency2_price_tax = fields.Float(compute='_compute_currency2_amount', string='Second Currency  Taxes', readonly=True, store=True)
    currency2_price_total = fields.Float(compute='_compute_currency2_amount', string='Second Currency Total', readonly=True, store=True)

