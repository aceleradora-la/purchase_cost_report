from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    purchase_cost_show_button = fields.Boolean(
        compute="_compute_purchase_cost_show_button",
        help="Verdadero si la factura es de proveedor, tiene OC con productos "
             "almacenables y Costos en Destino está instalado.",
    )

    @api.depends(
        "move_type",
        "invoice_line_ids.purchase_line_id",
        "invoice_line_ids.purchase_line_id.product_id.is_storable",
    )
    def _compute_purchase_cost_show_button(self):
        for move in self:
            if move.move_type not in ("in_invoice", "in_refund"):
                move.purchase_cost_show_button = False
                continue
            move.purchase_cost_show_button = any(
                line.purchase_line_id.product_id.is_storable
                for line in move.invoice_line_ids
                if line.purchase_line_id
            )

    def action_print_purchase_cost_report(self):
        """Abre el wizard de valuación partiendo desde la factura de proveedor."""
        self.ensure_one()
        pos = self.invoice_line_ids.purchase_line_id.order_id
        if not pos:
            raise UserError(
                _("Esta factura no tiene líneas vinculadas a una Orden de Compra.")
            )
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
