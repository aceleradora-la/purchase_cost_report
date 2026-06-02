from odoo import models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_print_purchase_cost_report(self):
        """Abre el wizard de valuación partiendo desde la factura de proveedor."""
        self.ensure_one()
        pos = self.invoice_line_ids.purchase_line_id.order_id
        if not pos:
            raise UserError(
                _("Esta factura no tiene líneas vinculadas a una Orden de Compra.")
            )
        # Si hay múltiples OC, abre la primera; el wizard queda vinculado a una sola OC
        order = pos[:1]
        wizard = self.env["purchase.cost.report.wizard"].create({"order_id": order.id})
        return {
            "name": _("Valuación en Moneda de Compra — %s") % order.name,
            "type": "ir.actions.act_window",
            "res_model": "purchase.cost.report.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }
