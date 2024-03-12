# -*- coding: utf-8 -*-
import logging
from odoo import models
_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def read_from_chatroom(self, field_read=None, load='_classic_read'):
        if not field_read:
            field_read = self.env['acrux.chat.conversation'].get_product_fields_to_read()
        return self.sudo().read(fields=field_read, load=load)

    def _set_image_1920(self):
        res = super(ProductProduct, self)._set_image_1920()
        Att = self.env['ir.attachment'].sudo()
        for rec in self:
            crr = Att.search([('res_model', '=', 'product.product'), ('res_id', '=', rec.id)], limit=1)
            if crr:
                crr.unlink()
        return res
    
    def _compute_image_1920(self):
        for record in self:
            record.image_1920 = record.image_variant_1920 or record.product_tmpl_id.image_1920
            Att = self.env['ir.attachment'].sudo()
            if record.image_1920:
                attac_id = Att.search([('res_model', '=', 'product.product'), ('res_id', '=', record.id)], limit=1)
                if not attac_id:
                    attac_id = Att.create({'name': record.name,
                                            'type': 'binary',
                                            'datas': record.image_1920,
                                            'store_fname': record.name,
                                            'res_model': 'product.product',
                                            'res_id': record.id})
                    attac_id.generate_access_token()

    def action_attach_product(self):
        for rec in self.search([]):
            rec._compute_image_1920()