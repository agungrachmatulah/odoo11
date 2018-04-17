# -*- coding: utf-8 -*-
""" Payment Statement in Bank """
from odoo import api, fields, models
MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
}


class AccountPaymentInherit(models.Model):
    _inherit = "account.payment"

    statement_id = fields.Many2one(
        'account.bank.statement', string='Bank Statement'
    )

    @api.multi
    def post(self):
        '''After create account.payment, will create a statement line.

        :return:
        '''
        res = super(AccountPaymentInherit, self).post()
        for rec in self:
            if rec.statement_id:
                if rec.partner_type == 'supplier':
                    amount = 0 - rec.amount
                else:
                    amount = rec.amount
                vals = {
                    'statement_id': rec.statement_id.id,
                    'date': rec.payment_date,
                    'name': '-',
                    'partner_id': rec.partner_id.id,
                    'ref': rec.name,
                    'amount': amount
                }
                self.env['account.bank.statement.line'].create(vals)
        return res

class AccountRegisterPaymentsInherit(models.TransientModel):
    _inherit = "account.register.payments"

    statement_id = fields.Many2one(
        'account.bank.statement', string='Bank Statement'
    )

    @api.multi
    def _prepare_payment_vals(self, invoices):
        '''Overide to include statement id.

        :param invoices: The invoices that should have the same commercial partner and the same type.
        :return: The payment values as a dictionary with statement_id included.
        '''
        res = super(AccountRegisterPaymentsInherit, self)._prepare_payment_vals(invoices)
        res['statement_id'] = self.statement_id.id
        return res