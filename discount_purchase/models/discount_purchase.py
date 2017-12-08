# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning


class Discount(models.Model):
    """new class about discount purchase"""
    _name = "discount.purchase"
    _order = "id asc"

    order_line_id = fields.Many2one('purchase.order.line',
                                 string='Purchase Order Line',
                                 readonly=True)
    type = fields.Selection([
        ('percentage', 'Percentage (%)'),
        ('fixed', 'Fixed Amount'),
        ], string='Discount Type', required=True, default='percentage')
    amount = fields.Float(string='Amount Discount', default=0)
    disc_value = fields.Float(string='Discount Value', readonly=True, store=True)
    subtotal = fields.Float(string='Subtotal', readonly=True, store=True)

    @api.onchange('type', 'amount')
    def onchange_discount(self):
        """function onchange_discount based on type and amount"""
        result = {}
        if not self.type or not self.amount or not self.order_line_id:
            return result
        if self.type == 'percentage' and self.amount > 100:
            raise Warning('Amount cannot more than 100 if type is percentage')
        if self.type == 'fixed' and self.amount > self.order_line_id.net_price:
            raise Warning('Amount cannot more than Net Price (Unit Price After Discount)')
        return result
