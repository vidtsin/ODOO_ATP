# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Bizople Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

import logging
from odoo import http, tools, _
from odoo.http import request
import werkzeug
import re
from odoo.addons.web.controllers.main import ensure_db, Home
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.exceptions import UserError
import urllib
import json

_logger = logging.getLogger(__name__)


class AuthSignupHome(Home):
    def do_signup(self, qcontext):
        """ Override do_signup for Create User & Partner with Extra fields.
        """
        values = {key: qcontext.get(key) for key in (
        'login', 'name', 'password', 'company_name',
        'street', 'over_18', 'phone')}
        assert values.get('password') == qcontext.get(
            'confirm_password'), "Passwords do not match; please retype them."
        supported_langs = [lang['code'] for lang in
                           request.env['res.lang'].sudo().search_read(
                               [], ['code'])]
        if request.lang in supported_langs:
            values['lang'] = request.lang
        self._signup_with_values(qcontext.get('token'), values)
        request.env.cr.commit()
        email = qcontext.get("login")
        user_ids = request.env['res.users'].search([("login", '=', email)])
        ip_address = http.request.httprequest.remote_addr
        city_name = ""
        country_name = ""
        try:
            urlFoLaction = "http://www.freegeoip.net/json/{0}".format(
                ip_address)
            locationInfo = json.loads(urllib.request.urlopen(urlFoLaction).read().decode("utf-8"))
            country_name = locationInfo['country_name']
            city_name = locationInfo['city']
        except:
            pass
        notification_email = ""
        config = request.env['res.config.settings'].sudo().search(
            [], order="id desc")
        if config:
            config = config[0]
            notification_email = config.email_notification or ""
        request.env['website.user.confirmation'].sudo().create({
            'user_id': user_ids[0].id,
            'partner_id': user_ids[0].partner_id.id,
            'confirmation_state': 'not_confirm',
            'country_name': country_name,
            'city_name': city_name,
            'ip_address': ip_address,
            'notification_email': notification_email
        })

    @http.route('/web/signup', type='http', auth='public', website=True,
                sitemap=False)
    def web_auth_signup(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()

        if not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise werkzeug.exceptions.NotFound()

        if 'error' not in qcontext and request.httprequest.method == 'POST':
            try:
                self.do_signup(qcontext)
                email = qcontext.get("login")
                user_ids = request.env['res.users'].search(
                    [("login", '=', email)])
                request.session.logout()
                request.env.cr.commit()
                return request.redirect(
                    "/signup-thank-you/signup-user?signup=%s" % user_ids[0].id)
            except UserError as e:
                qcontext['error'] = e.name or e.value
            except (SignupError, AssertionError) as e:
                if request.env["res.users"].sudo().search(
                        [("login", "=", qcontext.get("login"))]):
                    qcontext["error"] = _(
                        "Another user is already "
                        "registered using this email address.")
                else:
                    _logger.error("%s", e)
                    qcontext['error'] = _("Could not create a new account.")
        response = request.render('auth_signup.signup', qcontext)
        response.headers['X-Frame-Options'] = 'DENY'
        return response


class SignupThanks(http.Controller):

    @http.route('/user-confirm/user', type='http', auth="public",
                website=True)
    def signup_user_confirm_by_email(self, *args, **kw):
        user_id = kw.get("UserID", "0")
        website_user = request.env['website.user.confirmation'].sudo().browse(
            int(user_id))
        user = request.env['res.users'].sudo().browse(website_user.user_id)
        user.active = True
        website_user.sudo().confirmation_state = "confirm"
        return request.redirect("/web/login")

    @http.route('/signup-thank-you/signup-user', type='http', auth="public",
                website=True)
    def signup_restrict_users(self, *args, **kw):
        user_id = kw.get("signup", "0")
        user = request.env['res.users'].sudo().browse(int(user_id))
        partner_id = user.partner_id.id
        user.active = False
        request.env.cr.commit()
        notification_email = ""
        config = request.env['res.config.settings'].sudo().search(
            [], order="id desc")
        if config:
            config = config[0]
            notification_email = config.email_notification or ""
        signup_user_template = request.env.ref(
            'new_user_approval_bizople.email_template_apply_signup_confirmation_mail',
            raise_if_not_found=False)
        signup_user_template.sudo().email_from = notification_email
        signup_user_template.sudo().reply_to = notification_email
        signup_user_template.sudo().send_mail(partner_id, force_send=True)
        admin_user_template = request.env.ref(
            'new_user_approval_bizople.email_template_signup_user_confirmation_mail',
            raise_if_not_found=False)
        admin_user_template.sudo().email_from = notification_email
        admin_user_template.sudo().email_to = notification_email
        admin_user_template.sudo().reply_to = notification_email
        admin_user_template.sudo().send_mail(partner_id, force_send=True)
        return request.redirect("/signup-thank-you")

    @http.route('/signup-thank-you', type='http', auth="public", website=True)
    def signup_restrict(self, *args, **kw):
        return request.render("new_user_approval_bizople.appointment")
