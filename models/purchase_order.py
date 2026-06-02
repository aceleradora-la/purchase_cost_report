from odoo import models, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def action_print_cost_report(self):
        """Abre el wizard de valuación en moneda de la OC."""
        self.ensure_one()
        wizard = self.env["purchase.cost.report.wizard"].create({"order_id": self.id})
        return {
            "name": _("Valuación en Moneda de Compra — %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "purchase.cost.report.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }
