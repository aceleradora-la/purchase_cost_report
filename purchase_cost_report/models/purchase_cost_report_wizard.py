from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


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

    # ── Actualización de precios de venta ─────────────────────────────
    pricelist_id = fields.Many2one(
        "product.pricelist", string="Lista de Precios",
        help="Lista de precios donde se actualizarán los precios de venta.",
    )
    margin_percent = fields.Float(
        "Margen de Ganancia (%)", digits=(5, 2), default=0.0,
        help="Margen global aplicado sobre el costo total. Puede sobreescribirse por producto.",
    )
    price_date_start = fields.Date(
        "Vigencia desde", default=fields.Date.today,
        help="Fecha desde la que rigen los nuevos precios. El precio anterior se vence el día anterior.",
    )
    pricing_line_ids = fields.One2many(
        "purchase.cost.report.wizard.pricing", "wizard_id", string="Precios de Venta",
    )

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

        # Poblar líneas de pricing (una por producto)
        pricing_lines = []
        for line in data["lines"]:
            pricing_lines.append({
                "wizard_id": self.id,
                "product_id": line["product"].id,
                "cost_total": line["total_cost"],
            })
        if pricing_lines:
            self.env["purchase.cost.report.wizard.pricing"].create(pricing_lines)

    @api.onchange("margin_percent")
    def _onchange_margin_percent(self):
        """Propaga el margen global a las líneas que no tienen margen propio."""
        for line in self.pricing_line_ids:
            if not line.margin_percent:
                line.final_price = line.cost_total * (1.0 + self.margin_percent / 100.0)

    def action_print_pdf(self):
        """Imprime el PDF desde el wizard."""
        return (
            self.env.ref("purchase_cost_report.action_report_purchase_cost")
            .report_action(self.order_id)
        )

    def action_apply_prices(self):
        """Crea o actualiza ítems de lista de precios para cada producto del reporte."""
        self.ensure_one()
        if not self.pricelist_id:
            raise UserError(_("Seleccioná una lista de precios antes de aplicar los precios."))
        if not self.price_date_start:
            raise UserError(_("Indicá la fecha de vigencia de los nuevos precios."))
        if not self.pricing_line_ids:
            raise UserError(_("No hay productos con precio calculado para aplicar."))

        PricelistItem = self.env["product.pricelist.item"]
        pricelist = self.pricelist_id
        date_start = self.price_date_start
        date_end_prev = date_start - timedelta(days=1)
        company = self.order_id.company_id
        po_currency = self.order_id.currency_id
        pl_currency = pricelist.currency_id

        for line in self.pricing_line_ids:
            if not line.final_price:
                continue

            # Convertir precio a la moneda de la lista de precios si es necesario
            if pl_currency != po_currency:
                final_price_pl = po_currency._convert(
                    line.final_price, pl_currency, company, date_start
                )
            else:
                final_price_pl = line.final_price

            # Vencer o eliminar ítems existentes para este producto en esta lista
            existing = PricelistItem.search([
                ("pricelist_id", "=", pricelist.id),
                ("product_id", "=", line.product_id.id),
                ("compute_price", "=", "fixed"),
                "|",
                    ("date_end", "=", False),
                    ("date_end", ">=", date_start),
            ])
            for item in existing:
                item_date_start = item.date_start.date() if hasattr(item.date_start, "date") else item.date_start
                # Si el ítem empieza en date_end_prev o después, no se puede poner
                # date_end <= date_start → eliminarlo directamente.
                if not item_date_start or item_date_start >= date_end_prev:
                    item.unlink()
                else:
                    item.write({"date_end": date_end_prev})

            # Nota con el cálculo
            margin = line.margin_percent if line.margin_percent else self.margin_percent
            note_parts = [
                "OC: %s" % self.order_id.name,
                "Costo total: %s %s" % (
                    "%.2f" % line.cost_total,
                    po_currency.name,
                ),
                "Margen: %.2f%%" % margin,
            ]
            if pl_currency != po_currency:
                note_parts.append(
                    "Conversión %s → %s a fecha %s" % (
                        po_currency.name,
                        pl_currency.name,
                        date_start.strftime("%d/%m/%Y"),
                    )
                )
            note_parts.append("Precio final: %.2f %s" % (final_price_pl, pl_currency.name))
            note = " | ".join(note_parts)

            # Crear nuevo ítem
            PricelistItem.create({
                "pricelist_id": pricelist.id,
                "product_id": line.product_id.id,
                "applied_on": "0_product_variant",
                "compute_price": "fixed",
                "fixed_price": final_price_pl,
                "date_start": date_start,
                "date_end": False,
                "purchase_cost_note": note,
            })

            # Guardar historial
            self.env["purchase.cost.price.history"].create({
                "order_id": self.order_id.id,
                "pricelist_id": pricelist.id,
                "product_id": line.product_id.id,
                "date_applied": date_start,
                "currency_id": po_currency.id,
                "pricelist_currency_id": pl_currency.id,
                "cost_total": line.cost_total,
                "margin_percent": margin,
                "final_price": final_price_pl,
                "note": note,
            })

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Precios actualizados"),
                "message": _(
                    "%d precios actualizados en la lista '%s' con vigencia desde %s."
                ) % (
                    len(self.pricing_line_ids.filtered("final_price")),
                    pricelist.name,
                    date_start.strftime("%d/%m/%Y"),
                ),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }


class PurchaseCostReportWizardPricing(models.TransientModel):
    """Una fila por producto para definir el precio de venta a aplicar."""

    _name = "purchase.cost.report.wizard.pricing"
    _description = "Línea de Precio de Venta — Reporte Valuación"
    _order = "product_id"

    wizard_id = fields.Many2one("purchase.cost.report.wizard", ondelete="cascade")
    currency_id = fields.Many2one("res.currency", related="wizard_id.currency_id")

    product_id = fields.Many2one("product.product", string="Producto", readonly=True)
    cost_total = fields.Monetary(
        "Costo Total", currency_field="currency_id", readonly=True,
        help="Costo total del producto (proveedor + costos en destino) en moneda OC.",
    )
    margin_percent = fields.Float(
        "Margen (%)", digits=(5, 2),
        help="Si se deja en 0, se hereda el margen global del wizard.",
    )
    suggested_price = fields.Monetary(
        "Precio Sugerido", currency_field="currency_id", readonly=True,
        compute="_compute_suggested_price", store=True,
    )
    final_price = fields.Monetary(
        "Precio Final", currency_field="currency_id",
        help="Precio a aplicar en la lista. Se puede editar manualmente.",
    )

    note_preview = fields.Char(
        "Cálculo", compute="_compute_note_preview", store=False,
    )

    @api.depends("cost_total", "margin_percent", "final_price", "wizard_id.margin_percent", "wizard_id.currency_id")
    def _compute_note_preview(self):
        for line in self:
            margin = line.margin_percent if line.margin_percent else line.wizard_id.margin_percent
            currency = line.wizard_id.currency_id.name or ""
            line.note_preview = "Costo: %.2f %s | Margen: %.2f%% | Precio: %.2f %s" % (
                line.cost_total, currency, margin, line.final_price or 0.0, currency,
            )

    @api.depends("cost_total", "margin_percent", "wizard_id.margin_percent")
    def _compute_suggested_price(self):
        for line in self:
            margin = line.margin_percent if line.margin_percent else line.wizard_id.margin_percent
            line.suggested_price = line.cost_total * (1.0 + margin / 100.0)

    @api.onchange("suggested_price")
    def _onchange_suggested_price(self):
        """Pre-rellena final_price con el sugerido cuando cambia."""
        for line in self:
            if not line.final_price or line.final_price == 0:
                line.final_price = line.suggested_price

    @api.onchange("margin_percent")
    def _onchange_margin_percent(self):
        """Recalcula final_price cuando cambia el margen de la línea."""
        for line in self:
            margin = line.margin_percent if line.margin_percent else line.wizard_id.margin_percent
            line.final_price = line.cost_total * (1.0 + margin / 100.0)


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
        "Tipo de Cambio", digits=(16, 2), readonly=True,
        help="1 unidad de moneda OC = X unidades de moneda origen."
    )
    amount_po = fields.Monetary(
        "Monto en Moneda OC", currency_field="currency_id", readonly=True,
        help="Monto convertido a la moneda de la Orden de Compra."
    )
