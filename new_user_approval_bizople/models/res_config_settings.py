# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import AccessDenied


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    email_notification = fields.Char(
        "Email Notification", default="odoo@example.com")
    is_email_validation = fields.Boolean("Email Validation")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            email_notification=get_param('website.email_notification'),
            is_email_validation=get_param('website.is_email_validation')
        )
        return res

    def set_values(self):
        if not self.user_has_groups('website.group_website_designer'):
            raise AccessDenied()
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('website.email_notification', self.email_notification)
        set_param('website.is_email_validation', self.is_email_validation)
