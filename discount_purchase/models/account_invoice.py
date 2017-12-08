# coding: utf-8
""" file Account Invoice"""
from openerp import api, fields, models, _
from odoo.addons import decimal_precision as dp
from openerp.exceptions import  Warning
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class AccountInvoice(models.Model):
    """class Account Invoice"""
    _inherit = "account.invoice"

    @api.multi
    def get_taxes_values(self):
        """replace base function get_taxes_values for discount"""
        tax_grouped = {}
        for line in self.invoice_line_ids:
            price_unit = line.price_unit - (line.discount or 0.0)
            taxes = line.invoice_line_tax_ids.compute_all(price_unit,
                                                          self.currency_id,
                                                          line.quantity,
                                                          line.product_id,
                                                          self.partner_id)['taxes']
            for tax in taxes:
                val = self._prepare_tax_line_vals(line, tax)
                key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)

                if key not in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
        return tax_grouped
    
    def _prepare_invoice_line_from_po_line(self, line):
        """replace base function for edit discount"""
        if line.product_id.purchase_method == 'purchase':
            qty = line.product_qty - line.qty_invoiced
        else:
            qty = line.qty_received - line.qty_invoiced
        if float_compare(qty, 0.0, precision_rounding=line.product_uom.rounding) <= 0:
            qty = 0.0
        taxes = line.taxes_id
        invoice_line_tax_ids = line.order_id.fiscal_position_id.map_tax(taxes)
        invoice_line = self.env['account.invoice.line']
        data = {
            'purchase_line_id': line.id,
            'name': line.order_id.name+': '+line.name,
            'origin': line.order_id.origin,
            'uom_id': line.product_uom.id,
            'product_id': line.product_id.id,
            'account_id': invoice_line.with_context({'journal_id': self.journal_id.id,
                                                     'type': 'in_invoice'})._default_account(),
            'price_unit': line.order_id.currency_id.with_context(date=self.date_invoice).compute(line.price_unit, self.currency_id, round=False),
            'quantity': qty,
            'discount': line.order_id.currency_id.with_context(date=self.date_invoice).compute(line.discount, self.currency_id, round=False), #Discount in vendor bill
            'account_analytic_id': line.account_analytic_id.id,
            'analytic_tag_ids': line.analytic_tag_ids.ids,
            'invoice_line_tax_ids': invoice_line_tax_ids.ids
        }
        account = invoice_line.get_invoice_line_account('in_invoice', line.product_id,
                                                        line.order_id.fiscal_position_id,
                                                        self.env.user.company_id)
        if account:
            data['account_id'] = account.id
        return data

    @api.model
    def _anglo_saxon_purchase_move_lines(self, i_line, res):
        """ Replace base function
        Return the additional move lines for purchase invoices and refunds.

        i_line: An account.invoice.line object.
        res: The move line entries produced so far by the parent move_line_get.
        """
        inv = i_line.invoice_id
        company_currency = inv.company_id.currency_id
        if i_line.product_id and i_line.product_id.valuation == 'real_time' and i_line.product_id.type == 'product':
            # get the fiscal position
            fpos = i_line.invoice_id.fiscal_position_id
            # get the price difference account at the product
            acc = i_line.product_id.property_account_creditor_price_difference
            if not acc:
                # if not found on the product get the price difference account at the category
                acc = i_line.product_id.categ_id.property_account_creditor_price_difference_categ
            acc = fpos.map_account(acc).id
            # reference_account_id is the stock input account
            reference_account_id = i_line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=fpos)['stock_input'].id
            diff_res = []
            # calculate and write down the possible price difference between invoice price and product price
            for line in res:
                if line.get('invl_id', 0) == i_line.id and \
                    reference_account_id == line['account_id']:
                    valuation_price_unit = i_line.product_id.uom_id._compute_price(i_line.product_id.standard_price, i_line.uom_id)
                    if i_line.product_id.cost_method != 'standard' and i_line.purchase_line_id:
                        #for average/fifo/lifo costing method, fetch real cost price from incomming moves
                        valuation_price_unit = i_line.purchase_line_id.product_uom._compute_price(i_line.purchase_line_id.price_unit, i_line.uom_id)
                        stock_move_obj = self.env['stock.move']
                        valuation_stock_move = stock_move_obj.search([('purchase_line_id',
                                                                       '=',
                                                                       i_line.purchase_line_id.id),
                                                                      ('state', '=', 'done')])
                        if valuation_stock_move:
                            valuation_price_unit_total = 0
                            valuation_total_qty = 0
                            for val_stock_move in valuation_stock_move:
                                valuation_price_unit_total += val_stock_move.price_unit * val_stock_move.product_qty
                                valuation_total_qty += val_stock_move.product_qty
                            valuation_price_unit = valuation_price_unit_total / valuation_total_qty
                            valuation_price_unit = i_line.product_id.uom_id._compute_price(valuation_price_unit, i_line.uom_id)
                    if inv.currency_id.id != company_currency.id:
                        valuation_price_unit = company_currency.with_context(date=inv.date_invoice).compute(valuation_price_unit, inv.currency_id, round=False)
                    if valuation_price_unit != i_line.price_unit and \
                        line['price_unit'] == i_line.price_unit and acc:
                        # price with discount and without tax included
                        # edit 1 line about discount in price unit
                        price_unit = i_line.price_unit - (i_line.discount or 0.0)
                        tax_ids = []
                        if line['tax_ids']:
                            #line['tax_ids'] is like [(4, tax_id, None), (4, tax_id2, None)...]
                            taxes = self.env['account.tax'].browse([x[1] for x in line['tax_ids']])
                            price_unit = taxes.compute_all(price_unit, currency=inv.currency_id,
                                                           quantity=1.0)['total_excluded']
                            for tax in taxes:
                                tax_ids.append((4, tax.id, None))
                                for child in tax.children_tax_ids:
                                    if child.type_tax_use != 'none':
                                        tax_ids.append((4, child.id, None))
                        price_before = line.get('price', 0.0)
                        line.update({'price': company_currency.round(valuation_price_unit * line['quantity'])})
                        diff_res.append({
                            'type': 'src',
                            'name': i_line.name[:64],
                            'price_unit': company_currency.round(price_unit - valuation_price_unit),
                            'quantity': line['quantity'],
                            'price': company_currency.round(price_before - line.get('price', 0.0)),
                            'account_id': acc,
                            'product_id': line['product_id'],
                            'uom_id': line['uom_id'],
                            'account_analytic_id': line['account_analytic_id'],
                            'tax_ids': tax_ids,
                            })
            return diff_res
        return []
    

class AccountInvoiceLine(models.Model):
    """class Account Invoice Line"""
    _inherit = "account.invoice.line"

    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
                 'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id',
                 'invoice_id.company_id', 'invoice_id.date_invoice')
    def _compute_total_price(self):
        """replace base function effect discount"""
        for line in self:
            price = line.price_unit - (line.discount or 0.0)
            taxes = line.invoice_line_tax_ids.compute_all(price,
                                                          line.invoice_id.currency_id,
                                                          line.quantity,
                                                          product=line.product_id,
                                                          partner=line.invoice_id.partner_id)
            line.price_total = taxes['total_included']

    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
                 'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id',
                 'invoice_id.company_id', 'invoice_id.date_invoice')
    def _compute_price(self):
        """replace base function effect discount"""
        currency = self.invoice_id and self.invoice_id.currency_id or None
        price = self.price_unit - (self.discount or 0.0)
        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(price, currency,
                                                          self.quantity,
                                                          product=self.product_id,
                                                          partner=self.invoice_id.partner_id)
        self.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else self.quantity * price
        self.price_total = taxes['total_included'] if taxes else self.price_subtotal
        if self.invoice_id.currency_id and \
            self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
            price_subtotal_signed = self.invoice_id.currency_id.with_context(date=self.invoice_id.date_invoice).compute(price_subtotal_signed, self.invoice_id.company_id.currency_id)
        sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
        self.price_subtotal_signed = price_subtotal_signed * sign
