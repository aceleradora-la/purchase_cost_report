from odoo import models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_print_purchase_cost_report(self):
        """Abre el reporte de valuación en moneda de la OC, partiendo desde la factura de proveedor."""
        self.ensure_one()
        pos = self.invoice_line_ids.purchase_line_id.order_id
        if not pos:
            raise UserError(
                _("Esta factura no tiene líneas vinculadas a una Orden de Compra.")
            )
        return self.env.ref(
            "purchase_cost_report.action_report_purchase_cost"
        ).report_action(pos)
