# -*- coding: utf-8 -*-

import json
import requests

from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.exceptions import UserError

class ZaloConfiguration(models.TransientModel):
    _name = 'zalo.message.wizard'
    _description = 'Zalo Message Wizard'

    partner_ids = fields.Many2many('res.partner', string="Contacts")
    message = fields.Text('Message')
    zalo_message_id = fields.Many2one('zalo.message')

    def action_send(self):
        zalo_configuration = self.env.ref('zalo_configuration.zalo_configuration')

        for partner in self.partner_ids:
            if partner.zalo_user_id:
                partner = zalo_configuration.get_user_profile(partner.zalo_user_id)

                # send message from OA to user
                contact_id = self.env['acrux.chat.conversation'].search([('res_partner_id','=',partner.id),('agent_id','=',self._uid)],order="id desc", limit=1)
                if not contact_id:
                    contact_id = self.env['acrux.chat.conversation'].create({
                        'name': partner.name,
                        'number': partner.phone or '',
                        'agent_id': self._uid,
                        'res_partner_id': partner.id,
                    })
                msg_data = {
                    'text': self.message, 
                    'from_me': True, 
                    'ttype': 'text', 
                    'contact_id': contact_id.id, 
                    'res_model': False, 
                    'res_id': False
                }
                AcruxChatMessages = self.env['acrux.chat.message']
                message_obj = AcruxChatMessages.create(msg_data)
                partner = message_obj.contact_id.res_partner_id
                access_token = self.env['zalo.configuration'].get_access_token()
                url = 'https://openapi.zalo.me/v3.0/oa/message/cs'
                header = {
                    'Content-Type': 'application/json',
                    'access_token': access_token,
                }
                body = {
                    "recipient":{
                        "user_id": partner.zalo_user_id
                    },
                    "message": {
                        'text': self.message
                    }
                }
                resp = requests.post(url=url, headers=header, data=json.dumps(body))
                resp_json = resp.json()
                if resp_json.get('error', False):
                    raise UserError(resp_json.get('message'))
                
                # check Topic, if not create new
                zalo_message_id = self.zalo_message_id
                if not zalo_message_id:
                    zalo_message_id = self.zalo_message_id.create({
                        'message': self.message,
                        'line_ids': [(0, 0, {'partner_id': partner_id.id}) for partner_id in self.partner_ids.filtered(lambda x: x.zalo_user_id)],
                        'partner_ids': [(6, 0, self.partner_ids.filtered(lambda x: x.zalo_user_id).ids)],
                    })
                else:
                    # check existed contact in line
                    existted_partner_id = zalo_message_id.line_ids.filtered(lambda x: x.partner_id.id in self.partner_ids.ids)
                    if not existted_partner_id:
                        # add contact
                        zalo_message_id.line_ids = [(0, 0, {'partner_id': partner_id.id}) for partner_id in self.partner_ids.filtered(lambda x: x.zalo_user_id)]
                    # reset time message, seen, received
                    zalo_message_id.line_ids.write({'time_message': fields.Datetime.now(),'time_received': False,'time_seen': False})