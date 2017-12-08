# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning


class PurchaseOrderLine(models.Model):
    """Inherit model purchase order line"""
    _inherit = "purchase.order.line"

    @api.depends('price_unit', 'purch_discount_ids', 'discount')
    def _compute_net_price(self):
        """function for compute value of net_price"""
        for line in self:
            line.button_discount()
            line.update({
                'net_price': line.price_unit - line.discount,
            })

    discount = fields.Float(string='Discount', digits=dp.get_precision('Discount'),
                            default=0.0, readonly=True, copy=False,
                            help = "Discount of Purchase Order Line")
    purch_discount_ids = fields.One2many('discount.purchase', 'order_line_id',
                                         string='Discount Lines',
                                         help='List of Discount')
    net_price = fields.Float(string='Net Unit Price', compute='_compute_net_price',
                             store=True, readonly=True,
                             help='Unit Price after discount',
                             digits=dp.get_precision('Product Price'))

    def action_list_discount(self):
        """function in button for show list of discount"""
        self.ensure_one()
        view = self.env.ref('discount_purchase.discount_purchase_line_view_inherit')

        return {
            'name': _('Discount Order Line'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.order.line',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': self.id,
            'context': dict(
                self.env.context,
            ),
        }

    @api.multi
    def button_discount(self):
        """confirm button in view of discount list"""
        for this in self:
            if this.purch_discount_ids:
                total_disc = 0
                price_after_discount = 0
                first_discout = this.purch_discount_ids[0]
                for disc in this.purch_discount_ids:
                    if first_discout.id == disc.id:
                        if disc.type == 'percentage':
                            disc.disc_value = (disc.amount/100)*this.price_unit
                            disc.subtotal = this.price_unit - disc.disc_value
                        elif disc.type == 'fixed':
                            disc.disc_value = disc.amount
                            disc.subtotal = this.price_unit - disc.amount
                        price_after_discount = disc.subtotal
                        total_disc += disc.disc_value
                    else:
                        if disc.type == 'percentage':
                            disc.disc_value = (disc.amount/100)*price_after_discount
                            disc.subtotal = price_after_discount - disc.disc_value
                        elif disc.type == 'fixed':
                            disc.disc_value = disc.amount
                            disc.subtotal = price_after_discount - disc.amount
                        price_after_discount = disc.subtotal
                        total_disc += disc.disc_value
                this.discount = total_disc
            else:
                this.discount = 0
        return True

    @api.multi
    def button_apply_all(self):
        """confirm for apply all this discount"""
        for this in self:
            list_disc = []
            if this.purch_discount_ids:
                for disc in this.purch_discount_ids:
                    dict_disc = {}
                    dict_disc['type'] = disc.type
                    dict_disc['amount'] = disc.amount
                    list_disc.append(dict_disc)
            if this.order_id and this.order_id.order_line:
                for line in this.order_id.order_line:
                    if line.id != this.id:
                        if line.purch_discount_ids:
                            for line_disc in line.purch_discount_ids:
                                line_disc.unlink()
                        if list_disc:
                            for add_disc in list_disc:
                                if 'type' in add_disc and 'amount' in add_disc:
                                    self.env['discount.purchase'].create({
                                        'order_line_id' : line.id,
                                        'type' : add_disc['type'],
                                        'amount' : add_disc['amount'],
                                        })
                    line.button_discount()
        return True

    @api.depends('product_qty', 'price_unit', 'taxes_id', 'discount', 'net_price')
    def _compute_amount(self):
        """replace base function for compute price tax, total, subtotal"""
        for line in self:
            taxes = line.taxes_id.compute_all(line.net_price, line.order_id.currency_id,
                                              line.product_qty, product=line.product_id,
                                              partner=line.order_id.partner_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    @api.multi
    def write(self, vals):
        res = super(PurchaseOrderLine, self).write(vals)
        for line in self:
            if 'price_unit' in vals and line.purch_discount_ids:
                line.button_discount()
        return res

#     @api.multi
#     def copy(self, default=None):
#         new_poline = super(PurchaseOrderLine, self).copy(default=default)
#         for line in new_poline:
#             line.discount = 0
#         return new_poline
