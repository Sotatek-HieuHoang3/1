# -*- coding: utf-8 -*-

import json
import base64
import requests

from datetime import datetime, timedelta
from odoo import models, fields, api, _, tools
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import logging
from odoo.http import request
from odoo.exceptions import ValidationError, UserError
_logger = logging.getLogger(__name__)

class ZaloConfiguration(models.Model):
    _inherit = 'zalo.configuration'
    
    mapping_partner_ids = fields.One2many('zalo.configuration.mapping', 'config_id', 'Not Mapping Contacts')

    def _action_get_user_id(self, datas = [], offset=0):
        url = 'https://openapi.zalo.me/v2.0/oa/listrecentchat?data={"offset":%d,"count":10}' % offset
        header = {
            'access_token': self.get_access_token(),
        }
        resp = requests.get(url=url, headers=header)
        resp_json = resp.json()

        if resp_json.get('error', False):
            raise UserError(resp_json.get('message'))

        datas += resp_json['data']

        if len(resp_json['data']) == 10:
            offset += 1
            self._action_get_user_id(datas, offset)

        return datas

    def action_get_user_ids(self):
        partner_ids = self.env['res.partner'].search([('zalo_user_id','!=',False)])
        zalo_user_ids = self.mapping_partner_ids.mapped('zalo_user_id')

        create_datas = []
        datas = self._action_get_user_id()
        for data in datas:
            # check exist_from_contact
            existed_from_contact = partner_ids.filtered(lambda p: p.zalo_user_id == data['from_id'])
            if not existed_from_contact:
                if data['from_id'] not in zalo_user_ids:
                    create_datas.append((0, 0, {
                        'name': data['from_display_name'],
                        'message': data.get('message', ''),
                        'zalo_user_id': data['from_id'],
                        'partner_id': existed_from_contact and existed_from_contact[0].id or False,
                    }))
                    zalo_user_ids.append(data['from_id'])
            # check existed_to_contact
            existed_to_contact = partner_ids.filtered(lambda p: p.zalo_user_id == data['to_id'])
            if not existed_to_contact:
                if data['to_id'] not in zalo_user_ids:
                    create_datas.append((0, 0, {
                        'name': data['to_display_name'],
                        'message': data.get('message', ''),
                        'zalo_user_id': data['to_id'],
                        'partner_id': existed_to_contact and existed_to_contact[0].id or False,
                    }))
                    zalo_user_ids.append(data['to_id'])

        self.mapping_partner_ids = create_datas
        for line in self.env.ref('zalo_configuration.zalo_configuration').mapping_partner_ids:
            line.action_mapping_contact()

    @api.model
    def execute_maintenance(self, days=21):
        ''' Call from cron.
            Delete attachment older than N days. '''
        Message = self.env['acrux.chat.message']
        date_old = datetime.now() - timedelta(days=int(days))
        date_old = date_old.strftime(DEFAULT_SERVER_DATE_FORMAT)
        mess_ids = Message.search([('res_model', '=', 'ir.attachment'),
                                   ('res_id', '!=', False),
                                   ('date_message', '<', date_old)])
        attach_to_del = mess_ids.mapped('res_id')
        erased_ids = Message.unlink_attachment(attach_to_del)
        for mess_id in mess_ids:
            if mess_id.res_id in erased_ids:
                text = '%s\n(Attachment removed)' % mess_id.text
                mess_ids.write({'text': text.strip(),
                                'res_id': False})
        _logger.info('________ | execute_maintenance: Deleting %s attachments older than %s' %
                     (len(attach_to_del), date_old))
        
class ZaloConfigurationMapping(models.Model):
    _name = 'zalo.configuration.mapping'

    config_id = fields.Many2one('zalo.configuration')
    name = fields.Char('Zalo Name')
    zalo_user_id = fields.Char('User Id')
    message = fields.Text('Message')
    partner_id = fields.Many2one('res.partner', 'Contact')
    active = fields.Boolean('Active', default=True)

    def action_mapping_contact(self):
        if not self.zalo_user_id:
            raise UserError('Please input Zalo User Id for mapping!')
        partner_id = None
        if not partner_id:
            partner_id = self.env['res.partner'].search([('zalo_user_id','=',self.zalo_user_id)], limit=1)
            if partner_id:
                partner_id.name = self.name
            else:
                access_token = self.config_id.get_access_token()
                url = 'https://openapi.zalo.me/v2.0/oa/getprofile?data={"user_id":"%s"}' % self.zalo_user_id.replace(' ','')
                header = {
                    'access_token': access_token,
                }
                resp = requests.get(url=url, headers=header)
                resp_json = resp.json()
                if resp_json.get('error', False):
                    raise UserError(resp_json.get('message'))
                # get avatar
                avatar_url = resp_json['data'].get('avatars',[]) and resp_json['data']['avatars'].get('240','') or resp_json['data'].get('avatar','')
                avatar = ''
                if avatar_url:
                    avatar_request = requests.get(avatar_url)
                    avatar = avatar_request.content
                partner_id = self.env['res.partner'].create({
                    'name': self.name,
                    'zalo_user_id': self.zalo_user_id,
                    'image_1920': base64.b64encode(avatar),
                })
        self.partner_id = partner_id.id
        # save message in post
        zalo_message_line_id = self.env['zalo.message.line'].sudo().search([('partner_id','=',partner_id.id)], limit=1, order="time_message desc")
        zalo_message_id = zalo_message_line_id.message_id
        if not zalo_message_id:
            zalo_message_id = self.env['zalo.message'].sudo().create({
                'message': self.message,
                'partner_ids': [(6, 0, partner_id.ids)],
                'line_ids': [(0, 0, {'partner_id': partner_id.id, 'time_received': datetime.now(), 'time_seen': datetime.now()}), ],
            })
        # tạo channel
        conversation = self.env['acrux.chat.conversation'].create({
            'name': self.name,
            'agent_id': self._uid,
            'res_partner_id': partner_id.id,
        })
        # tạo msg
        message_id = self.env['acrux.chat.message'].create({
            'text': self.message,
            'contact_id': conversation.id,
            'user_id': self._uid,
            'date_message': self.create_date,
            'ttype': 'text',
            'event': 'to_new',
        })
        data = {
            'connector_id': self.env['acrux.chat.connector'].search([], limit=1),
            'text': self.message,
            'contact_id': conversation.id,
            'ttype': 'text',
            'date_message': self.create_date,
            'from_me': False
        }
        limit = conversation.decide_first_status()
        limit, send_bus = conversation.new_message_hook(message_id, limit, data, conversation.last_sent)
        if conversation.env.context.get('downl_later'):
            self.env.cr.commit()
            conversation.with_context(not_download_profile_picture=False).update_conversation()
        if send_bus:
            data_to_send = conversation.build_dict(limit)
            conversation._sendone(conversation.get_bus_channel(), 'new_messages', data_to_send)
        self.active = False

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        for record in self:
            if record.partner_id and record.partner_id.zalo_user_id:
                record.zalo_user_id = record.partner_id.zalo_user_id
                record.name = record.name or record.partner_id.name