# -*- coding: utf-8 -*-
from odoo import models, fields


class InitFreeTestWizard(models.TransientModel):
    _name = 'acrux.chat.connector.scanqr.wizard'
    _description = 'Scan QR'

    connector_id = fields.Many2one('acrux.chat.connector', 'Connector', required=True,
                                   ondelete='cascade', default=lambda self: self.env['acrux.chat.connector'].search([], limit=1).id)
    ca_qr_code = fields.Binary('QR Code', related='connector_id.ca_qr_code')

    def action_ca_get_status(self):
        return self.connector_id.action_ca_get_status()

    def action_close(self):
        if not self.connector_id.ca_status:
            self.connector_id.action_ca_get_status()
