# -*- coding: utf-8 -*-

import json
import requests

from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.exceptions import UserError

class ZaloMessage(models.Model):
    _name = 'zalo.message'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Zalo Message'
    _rec_name = 'message'

    partner_ids = fields.Many2many('res.partner', string="Contacts")
    line_ids = fields.One2many('zalo.message.line', 'message_id', string="Detail")
    message = fields.Text('Message')

    def action_send(self):
        zalo_configuration = self.env.ref('zalo_configuration.zalo_configuration')
        if zalo_configuration.access_token:
            wizard = self.env['zalo.message.wizard'].create({
                'partner_ids': [(6, 0, self.partner_ids.filtered(lambda x: x.zalo_user_id).ids)],
                'message': '',
                'zalo_message_id': self.id
            })
            action = self.env.ref('zalo_connector.zalo_message_wizard_action').read([])[0]
            action['res_id'] = wizard.id
            return action

class ZaloMessageLine(models.Model):
    _name = 'zalo.message.line'

    message_id = fields.Many2one('zalo.message')
    partner_id = fields.Many2one('res.partner', string="Contacts")
    msg_id = fields.Char('OA Zalo Message')
    status = fields.Selection([
        ('sent', 'Sent'), ('seen', 'Seen'),
    ], string='Status')
    time_received = fields.Datetime("Recieved")
    time_seen = fields.Datetime("Seen")
    time_message = fields.Datetime('Time Message', default=fields.Datetime.now())