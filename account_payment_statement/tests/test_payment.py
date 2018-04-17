# -*- coding: utf-8 -*-
# pylint: disable=import-error,unused-import
import logging
from odoo import _
from odoo.addons.account.tests.account_test_classes import AccountingTestCase
import time

_logger = logging.getLogger(__name__)

class TestStatementPayment(AccountingTestCase):

    def setUp(self):
        super(TestStatementPayment, self).setUp()
        _logger.info(_('==*== Testing Statement Payment START ==*=='))
        _logger.info(_('==> Create Master Data'))

        _logger.info(_('>>create CoA'))
        self.account_receivable = self.env['account.account.type'].search(
            [('name', '=', 'Receivable')], limit=1)
        self.account_payable = self.env['account.account.type'].search(
            [('name', '=', 'Payable')], limit=1)
        self.account_ex = self.env['account.account.type'].search(
            [("name", "=", "Expenses")], limit=1)

        self.payable_account = self.env['account.account'].create({
            'name': 'Account Payable',
            'code': '210201090',
            'user_type_id': self.account_payable.id,
            'reconcile': True,
        })
        self.receivable_account = self.env['account.account'].create({
            'name': 'Account Receivable',
            'code': '210201091',
            'user_type_id': self.account_receivable.id,
            'reconcile': True,
        })
        self.ex_account = self.env['account.account'].create({
            'name': 'Account Receivable',
            'code': '210201096',
            'user_type_id': self.account_ex.id,
            'reconcile': True,
        })
        _logger.info(_('>>create Partner'))
        self.supplier = self.env['res.partner'].create({
            'name': 'Supplier',
            'supplier': True,
            'customer': False,
            'company_type': 'company',
            'property_account_receivable_id': self.receivable_account.id,
            'property_account_payable_id': self.payable_account.id,
        })
        self.customer = self.env['res.partner'].create({
            'name': 'Customer',
            'supplier': False,
            'customer': True,
            'company_type': 'company',
            'property_account_receivable_id': self.receivable_account.id,
            'property_account_payable_id': self.payable_account.id,
        })

        _logger.info(_('create Journal Bank'))
        self.bank_journal = self.env['account.journal'].create({'name': 'Bank', 'type': 'bank', 'code': '009'})
        self.account_bank = self.bank_journal.default_debit_account_id

        self.payment_method_manual_in = self.env.ref("account.account_payment_method_manual_in")
        self.payment_method_manual_out = self.env.ref("account.account_payment_method_manual_out")

        self.statment_bank = self.env['account.bank.statement'].create({
            'journal_id': self.bank_journal.id,
        })

    def create_invoice(self, amount=100, type=False, currency_id=None, partner=None):
        """ Returns an open invoice """
        if type == 'in_invoice':
            account_coa = partner.property_account_payable_id.id
        else:
            account_coa = partner.property_account_receivable_id.id
        invoice = self.env['account.invoice'].create({
            'partner_id': partner.id,
            'reference_type': 'none',
            'currency_id': currency_id,
            'name': type,
            'account_id': account_coa,
            'type': type,
            'date_invoice': time.strftime('%Y') + '-06-26',
        })
        self.env['account.invoice.line'].create({
            'quantity': 1,
            'price_unit': amount,
            'invoice_id': invoice.id,
            'name': 'something',
            'account_id': self.ex_account.id,
        })
        invoice.action_invoice_open()
        return invoice

    def invoice_payment(self, invoice, method):
        """  """
        register_payments = self.env['account.register.payments'].with_context(active_ids=invoice).create({
            'payment_date': time.strftime('%Y') + '-07-15',
            'journal_id': self.bank_journal.id,
            'statement_id': self.statment_bank.id,
            'payment_method_id': method.id,
        })
        register_payments.create_payments()
        payment = self.env['account.payment'].search([], order="id desc", limit=1)
        statement_line = self.env['account.bank.statement.line'].search([('ref', '=', payment.name)])
        return statement_line

    def test_payment(self):
        _logger.info(_('>>create CI'))
        ci1 = self.create_invoice(amount=7000, type='out_invoice',
                                  currency_id=self.env.user.company_id.currency_id.id,
                                  partner=self.customer)
        ci2 = self.create_invoice(amount=500, type='out_invoice',
                                  currency_id=self.env.user.company_id.currency_id.id,
                                  partner=self.customer)
        ci3 = self.create_invoice(amount=1500, type='out_invoice',
                                  currency_id=self.env.user.company_id.currency_id.id,
                                  partner=self.customer)

        _logger.info(_('>>create VB'))
        vb1 = self.create_invoice(amount=7000, type='in_invoice',
                                  currency_id=self.env.user.company_id.currency_id.id,
                                  partner=self.supplier)
        vb2 = self.create_invoice(amount=7000, type='in_invoice',
                                  currency_id=self.env.user.company_id.currency_id.id,
                                  partner=self.supplier)
        vb3 = self.create_invoice(amount=5000, type='in_invoice',
                                  currency_id=self.env.user.company_id.currency_id.id,
                                  partner=self.supplier)

        _logger.info(_('Test Create Payment CI1'))
        self.assertEqual(self.invoice_payment(ci1.id, self.payment_method_manual_in).amount, 7000)
        _logger.info(_('Test Create Payment CI2 n CI3'))
        self.assertEqual(self.invoice_payment([ci2.id, ci3.id], self.payment_method_manual_in).amount, 2000)

        _logger.info(_('Test Create Payment VB1'))
        self.assertEqual(self.invoice_payment(vb1.id, self.payment_method_manual_in).amount, -7000)
        _logger.info(_('Test Create Payment VB2 n VB3'))
        self.assertEqual(self.invoice_payment([vb2.id, vb3.id], self.payment_method_manual_in).amount, -12000)
