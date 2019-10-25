# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Bizople
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class UserRejectMessageWizard(models.TransientModel):
    _name = "user.reject.message.wizard"

    @api.model
    def default_get(self, fields):
        res = super(UserRejectMessageWizard, self).default_get(fields)
        active_id = self.env.context.get("active_id", False)
        if not active_id:
            return res
        website_user_id = self.env['website.user.confirmation'].browse(
            active_id)
        res['website_user_id'] = active_id
        res['partner_id'] = website_user_id.partner_id.id
        return res

    msg = fields.Text("Message")
    website_user_id = fields.Many2one(
        "website.user.confirmation", "Website User")
    partner_id = fields.Many2one("res.partner", "Partner")

    @api.multi
    def get_reject_website_user(self):
        for obj in self:
            html_body = """
            <p>Hi %s,</p>
            <p>Your Account has been Rejected </p>
            <p>Reason for the rejection: </p>
            <p>%s</p>
            <p> Thank you </p>
            """ % (obj.partner_id.name, obj.msg)
            reject_template_id = self.env.ref(
                "new_user_approval_bizople.email_template_signup_user_reject_mail")
            config = self.env['res.config.settings'].sudo().search(
                [], order="id desc")
            if config:
                config = config[0]
                notification_email = config.email_notification or ""
                reject_template_id.sudo().email_from = notification_email
                reject_template_id.sudo().reply_to = notification_email
                reject_template_id.sudo().body_html = html_body
                partner_id = obj.partner_id.id
                reject_template_id.sudo().send_mail(partner_id, force_send=True)
            obj.website_user_id.confirmation_state = "reject"
        return True
