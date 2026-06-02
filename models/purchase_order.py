from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    purchase_cost_show_button = fields.Boolean(
        compute="_compute_purchase_cost_show_button",
        help="Verdadero si la OC tiene al menos un producto almacenable y "
             "Costos en Destino está instalado.",
    )

    @api.depends("order_line.product_id", "order_line.product_id.detailed_type")
    def _compute_purchase_cost_show_button(self):
        for order in self:
            order.purchase_cost_show_button = (
                order.state in ("purchase", "done")
                and any(
                    line.product_id.detailed_type == "product"
                    for line in order.order_line
                    if line.product_id
                )
            )

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
