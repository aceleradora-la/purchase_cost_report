from odoo import fields, models


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    purchase_cost_note = fields.Text(
        "Nota de Valuación",
        help="Detalle del cálculo que originó este precio (OC, costo base, margen, TC, etc.).",
    )
