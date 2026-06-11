from odoo import fields, models


class PurchaseCostPriceHistory(models.Model):
    """Historial de actualizaciones de precio generadas desde el reporte de valuación."""

    _name = "purchase.cost.price.history"
    _description = "Historial de Precios — Reporte de Valuación"
    _order = "date_applied desc, id desc"
    _rec_name = "product_id"

    order_id = fields.Many2one("purchase.order", string="Orden de Compra", readonly=True, index=True)
    pricelist_id = fields.Many2one("product.pricelist", string="Lista de Precios", readonly=True, index=True)
    product_id = fields.Many2one("product.product", string="Producto", readonly=True, index=True)
    date_applied = fields.Date("Vigencia desde", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Moneda OC", readonly=True)
    pricelist_currency_id = fields.Many2one("res.currency", string="Moneda Lista", readonly=True)
    cost_total = fields.Monetary("Costo Total", currency_field="currency_id", readonly=True)
    margin_percent = fields.Float("Margen (%)", digits=(5, 2), readonly=True)
    final_price = fields.Monetary("Precio Aplicado", currency_field="pricelist_currency_id", readonly=True)
    note = fields.Text("Detalle del cálculo", readonly=True)
