from odoo import api, fields, models


class PurchaseCostReportWizard(models.TransientModel):
    """
    Wizard de visualización on-screen del reporte de valuación.
    Se crea con una OC, computa las líneas y se abre en un diálogo.
    """

    _name = "purchase.cost.report.wizard"
    _description = "Valuación en Moneda de Compra"

    order_id = fields.Many2one("purchase.order", string="Orden de Compra", required=True, readonly=True)
    currency_id = fields.Many2one("res.currency", related="order_id.currency_id")
    company_id = fields.Many2one("res.company", related="order_id.company_id")

    product_line_ids = fields.One2many(
        "purchase.cost.report.wizard.product", "wizard_id", string="Productos"
    )
    lc_line_ids = fields.One2many(
        "purchase.cost.report.wizard.lc", "wizard_id", string="Detalle por Producto"
    )
    lc_summary_ids = fields.One2many(
        "purchase.cost.report.wizard.lc.summary", "wizard_id", string="Resumen Costos en Destino"
    )

    total_product = fields.Monetary("Total Proveedor", currency_field="currency_id", readonly=True)
    total_lc = fields.Monetary("Total Costos Destino", currency_field="currency_id", readonly=True)
    total_all = fields.Monetary("Costo Total", currency_field="currency_id", readonly=True)
    lc_percentage = fields.Float("% Costos s/Compra", digits=(5, 2), readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        wizards = super().create(vals_list)
        for wizard in wizards:
            wizard._populate()
        return wizards

    def _populate(self):
        """Calcula y persiste las líneas del reporte usando la misma lógica del PDF."""
        report = self.env["report.purchase_cost_report.report_purchase_cost"]
        data = report._prepare_order_data(self.order_id)

        product_lines = []
        lc_lines = []

        for line in data["lines"]:
            product_lines.append(
                {
                    "wizard_id": self.id,
                    "product_id": line["product"].id,
                    "ordered_qty": line["ordered_qty"],
                    "received_qty": line["received_qty"],
                    "uom_id": line["uom"].id,
                    "product_unit_cost": line["product_unit_cost"],
                    "product_total_cost": line["product_total_cost"],
                    "lc_total": line["lc_total"],
                    "unit_cost": line["unit_cost"],
                    "total_cost": line["total_cost"],
                }
            )
            for lc in line["lc_lines"]:
                lc_lines.append(
                    {
                        "wizard_id": self.id,
                        "product_id": line["product"].id,
                        "landed_cost_id": lc["landed_cost"].id,
                        "vendor_bill_id": lc["vendor_bill"].id if lc["vendor_bill"] else False,
                        "date": lc["date"],
                        "ref_currency_id": lc["ref_currency"].id,
                        "amount_ref": lc["amount_ref"],
                        "amount_po": lc["amount_po"],
                    }
                )

        if product_lines:
            self.env["purchase.cost.report.wizard.product"].create(product_lines)
        if lc_lines:
            self.env["purchase.cost.report.wizard.lc"].create(lc_lines)

        # Resumen agrupado por LC (sin repetir por producto)
        lc_summary_lines = [
            {
                "wizard_id": self.id,
                "landed_cost_id": lcs["landed_cost"].id,
                "vendor_bill_id": lcs["vendor_bill"].id if lcs["vendor_bill"] else False,
                "date": lcs["date"],
                "ref_currency_id": lcs["ref_currency"].id,
                "amount_ref": lcs["amount_ref"],
                "exchange_rate": lcs["exchange_rate"],
                "amount_po": lcs["amount_po"],
            }
            for lcs in data["lc_summary"]
        ]
        if lc_summary_lines:
            self.env["purchase.cost.report.wizard.lc.summary"].create(lc_summary_lines)

        # Guardar totales y porcentaje en el wizard para mostrarlos en la vista
        self.write({
            "total_product": data["total_product"],
            "total_lc": data["total_lc"],
            "total_all": data["total_all"],
            "lc_percentage": data["lc_percentage"],
        })

    def action_print_pdf(self):
        """Imprime el PDF desde el wizard."""
        return (
            self.env.ref("purchase_cost_report.action_report_purchase_cost")
            .report_action(self.order_id)
        )


class PurchaseCostReportWizardProduct(models.TransientModel):
    _name = "purchase.cost.report.wizard.product"
    _description = "Línea de Producto — Reporte Valuación"
    _order = "product_id"

    wizard_id = fields.Many2one("purchase.cost.report.wizard", ondelete="cascade")
    currency_id = fields.Many2one("res.currency", related="wizard_id.currency_id")

    product_id = fields.Many2one("product.product", string="Producto", readonly=True)
    ordered_qty = fields.Float("Cant. Ord.", digits="Product Unit of Measure", readonly=True)
    received_qty = fields.Float("Cant. Rec.", digits="Product Unit of Measure", readonly=True)
    uom_id = fields.Many2one("uom.uom", string="UdM", readonly=True)
    product_unit_cost = fields.Monetary(
        "Costo Unit. Prov.", currency_field="currency_id", readonly=True
    )
    product_total_cost = fields.Monetary(
        "Total Proveedor", currency_field="currency_id", readonly=True
    )
    lc_total = fields.Monetary(
        "Costos Destino", currency_field="currency_id", readonly=True
    )
    unit_cost = fields.Monetary(
        "Costo Unit. Total", currency_field="currency_id", readonly=True
    )
    total_cost = fields.Monetary(
        "Costo Total", currency_field="currency_id", readonly=True
    )


class PurchaseCostReportWizardLC(models.TransientModel):
    _name = "purchase.cost.report.wizard.lc"
    _description = "Detalle Costo en Destino — Reporte Valuación"
    _order = "product_id, date"

    wizard_id = fields.Many2one("purchase.cost.report.wizard", ondelete="cascade")
    currency_id = fields.Many2one("res.currency", related="wizard_id.currency_id")

    product_id = fields.Many2one("product.product", string="Producto", readonly=True)
    landed_cost_id = fields.Many2one(
        "stock.landed.cost", string="Costo en Destino", readonly=True
    )
    vendor_bill_id = fields.Many2one(
        "account.move", string="Factura", readonly=True
    )
    date = fields.Date("Fecha", readonly=True)
    ref_currency_id = fields.Many2one("res.currency", string="Moneda Orig.", readonly=True)
    amount_ref = fields.Monetary(
        "Monto Origen", currency_field="ref_currency_id", readonly=True
    )
    amount_po = fields.Monetary(
        "Monto OC", currency_field="currency_id", readonly=True
    )


class PurchaseCostReportWizardLCSummary(models.TransientModel):
    """Un registro por cada Costo en Destino (agrupado, sin repetir por producto)."""

    _name = "purchase.cost.report.wizard.lc.summary"
    _description = "Resumen Costos en Destino — Reporte Valuación"
    _order = "date"

    wizard_id = fields.Many2one("purchase.cost.report.wizard", ondelete="cascade")
    currency_id = fields.Many2one("res.currency", related="wizard_id.currency_id")

    landed_cost_id = fields.Many2one(
        "stock.landed.cost", string="Costo en Destino", readonly=True
    )
    vendor_bill_id = fields.Many2one(
        "account.move", string="Factura", readonly=True
    )
    date = fields.Date("Fecha", readonly=True)
    ref_currency_id = fields.Many2one("res.currency", string="Moneda Orig.", readonly=True)
    amount_ref = fields.Monetary(
        "Monto Origen", currency_field="ref_currency_id", readonly=True,
        help="Monto en la moneda original de la factura del costo en destino."
    )
    exchange_rate = fields.Float(
        "Tipo de Cambio", digits=(16, 4), readonly=True,
        help="1 unidad de moneda OC = X unidades de moneda origen."
    )
    amount_po = fields.Monetary(
        "Monto en Moneda OC", currency_field="currency_id", readonly=True,
        help="Monto convertido a la moneda de la Orden de Compra."
    )
