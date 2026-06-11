from odoo import _, fields, models


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    purchase_cost_note = fields.Text(
        "Nota de Valuación",
        help="Detalle del cálculo que originó este precio (OC, costo base, margen, TC, etc.).",
    )

    def action_open_cost_history(self):
        self.ensure_one()
        domain = [("pricelist_id", "=", self.pricelist_id.id)]
        if self.product_id:
            domain.append(("product_id", "=", self.product_id.id))
        return {
            "name": _("Historial de Precios — %s") % (self.product_id.display_name or self.pricelist_id.name),
            "type": "ir.actions.act_window",
            "res_model": "purchase.cost.price.history",
            "view_mode": "list,form",
            "domain": domain,
            "target": "new",
        }
