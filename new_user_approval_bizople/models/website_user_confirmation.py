from odoo import models, fields, api


class WebsiteUserConfirmation(models.Model):
    _name = "website.user.confirmation"

    @api.depends("partner_id", "partner_id.email")
    def _get_user_email(self):
        for obj in self:
            user_email = ""
            if obj.partner_id:
                user_email = obj.partner_id.email
            obj.login = user_email

    user_id = fields.Integer("UserID")
    login = fields.Char("User Email", compute="_get_user_email", store=True)
    partner_id = fields.Many2one("res.partner", "Customer")
    confirmation_state = fields.Selection([
        ("not_confirm", "Not Confirm"),
        ("waiting", "Waiting"),
        ("confirm", "Confirmed"),
        ("reject", "Rejected")
    ], "Confirmation State", default="not_confirm")
    country_name = fields.Char("Country")
    city_name = fields.Char("City")
    ip_address = fields.Char("IP Address")
    notification_email = fields.Char("Notification Email")

    @api.multi
    def get_confirm_user(self):
        for obj in self:
            if not obj.user_id:
                continue
            notification_email = ""
            is_email_validation = False
            config = self.env['res.config.settings'].sudo().search(
                [], order="id desc")
            if config:
                config = config[0]
                notification_email = config.email_notification or ""
                if config.is_email_validation:
                    is_email_validation = True
            html_body1 = """
            <p><span style="font-size: 14px;">Thank You,</span><br>
            <br><span style="font-size: 14px;">Your account is now open and you 
            are able to view your price list. </span>
            </p>
            <p><span style="font-size: 14px;">Please login using the email 
            address and password chosen on registration.
            </span></p><p><span style="font-size: 14px;">We looking forward to 
            your custom and thank you for choosing us.</span></p>
            """
            para_ids = self.env['ir.config_parameter'].search([
                ("key", '=', "web.base.url")
            ])
            user = self.env['res.users'].browse(obj.user_id)
            if para_ids:
                url1 = para_ids[0].value
                url2 = "/user-confirm/user?UserID=%s" % obj.id
                final_url = url1 + url2
                html_body2 = """
                <p><span style="font-size: 14px;">Thank You,</span><br>
                <br><span style="font-size: 14px;">Your account is now open and you 
                are able to view your price list. </span>
                </p>
                <p><span style="font-size: 14px;">Please login using the email 
                address and password chosen on registration with below Link.
                </span></p><p><span style="font-size: 14px;">
                <strong><a href="%s" style=" color: #875A7B;">Click Here</a></strong>
                </span></p>
                """ % final_url
                confirm_template = self.env.ref(
                    "new_user_approval_bizople.email_template_signup_user_confirmation_done_mail",
                    raise_if_not_found=False)
                if is_email_validation:
                    html_data = html_body2
                    obj.confirmation_state = 'waiting'
                else:
                    html_data = html_body1
                    user.active = True
                    obj.confirmation_state = 'confirm'
                confirm_template.sudo().email_from = notification_email
                confirm_template.sudo().reply_to = notification_email
                confirm_template.sudo().body_html = html_data
                partner_id = obj.partner_id.id
                confirm_template.sudo().send_mail(partner_id, force_send=True)
        return True
