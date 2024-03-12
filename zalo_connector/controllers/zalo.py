# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.http import request
from datetime import datetime, timedelta

class ZaloControllers(http.Controller):

    @http.route('/zalo/webhook', type='json', auth='public', csrf=False)
    def zalo_webhook(self, **kw):
        record = http.request.env.ref('zalo_configuration.zalo_configuration').sudo()
        if request.httprequest and request.httprequest.data:
            data = json.loads(http.request.httprequest.data)
            sender = record.get_user_profile(data['sender']['id'])
            if data['event_name'] == 'follow':
                record.get_user_profile(data['follower']['id'])
            elif data['event_name'] == 'user_send_text':
                vals = {
                    'ttype': 'text',
                    'number': sender.phone or '',
                    'message': data['message']['text'],
                    'time': datetime.fromtimestamp(int(data['timestamp']) / 1000, tz=None),
                    'sender': sender.id,
                    'url': ''
                }
                conversation = request.env['acrux.chat.conversation'].sudo().new_message(vals)
            elif data['event_name'] == 'user_received_message':
                line_ids = request.env['zalo.message.line'].sudo().search([('time_received','=',False)])
                line_ids = line_ids.filtered(lambda x: x.partner_id.zalo_user_id == data['recipient']['id'])
                if line_ids:
                    line_ids.write({'status': 'sent','time_received': datetime.fromtimestamp(int(data['timestamp']) / 1000, tz=None)})
            elif data['event_name'] == 'user_seen_message':
                line_ids = request.env['zalo.message.line'].sudo().search([('time_seen', '=', False)])
                line_ids = line_ids.filtered(lambda x: x.partner_id.zalo_user_id == data['recipient']['id'])
                if line_ids:
                    line_ids.write({'status': 'seen', 'time_seen': datetime.fromtimestamp(int(data['timestamp']) / 1000, tz=None)})
                    line_ids.filtered(lambda x: not x.time_received).write({'time_received': datetime.fromtimestamp(int(data['timestamp']) / 1000, tz=None)})
            elif data['event_name'] in ['user_send_image','user_send_sticker']:
                for attachment in data['message']['attachments']:
                    vals = {
                        'ttype': attachment['type'],
                        'number': sender.phone or '',
                        'message': attachment['type'],
                        'time': datetime.fromtimestamp(int(data['timestamp']) / 1000, tz=None),
                        'sender': sender.id,
                        'url': attachment['payload']['url'],
                    }
                    conversation = request.env['acrux.chat.conversation'].sudo().new_message(vals)
            elif data['event_name'] == 'user_send_gif':
                for attachment in data['message']['attachments']:
                    vals = {
                        'ttype': attachment['type'],
                        'number': sender.phone or '',
                        'message': attachment['type'],
                        'time': datetime.fromtimestamp(int(data['timestamp']) / 1000, tz=None),
                        'sender': sender.id,
                        'url': attachment['payload']['url'],
                    }
                    conversation = request.env['acrux.chat.conversation'].sudo().new_message(vals)
            elif data['event_name'] == 'user_send_file':
                for attachment in data['message']['attachments']:
                    vals = {
                        'ttype': attachment['type'],
                        'number': sender.phone or '',
                        'message': attachment['payload']['name'],
                        'time': datetime.fromtimestamp(int(data['timestamp']) / 1000, tz=None),
                        'sender': sender.id,
                        'url': attachment['payload']['url'],
                    }
                    conversation = request.env['acrux.chat.conversation'].sudo().new_message(vals)
            elif data['event_name'] == 'user_send_link':
                for attachment in data['message']['attachments']:
                    vals = {
                        'ttype': 'text',
                        'number': sender.phone or '',
                        'message': data['message']['text'],
                        'time': datetime.fromtimestamp(int(data['timestamp']) / 1000, tz=None),
                        'sender': sender.id,
                        'url': attachment['payload']['url'],
                    }
                    conversation = request.env['acrux.chat.conversation'].sudo().new_message(vals)
        return {'code': 200, 'message': "Get Message Success!"}