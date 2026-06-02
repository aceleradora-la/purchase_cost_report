from odoo import models, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def action_print_cost_report(self):
        """Abre el reporte de valuación en moneda de la OC."""
        self.ensure_one()
        return self.env.ref(
            "purchase_cost_report.action_report_purchase_cost"
        ).report_action(self)
