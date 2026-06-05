from odoo import api, fields, models
from odoo.tools.float_utils import float_is_zero
from odoo.tools.misc import formatLang as _formatLang


class PurchaseCostReport(models.AbstractModel):
    """
    Reporte de valuación de recepciones en moneda de la Orden de Compra.

    Para cada producto de la OC muestra:
    - Costo del proveedor (directo de la OC, en moneda de la OC)
    - Costos en destino (cada Landed Cost convertido a moneda de la OC
      usando el TC de la fecha del comprobante del costo en destino)
    - Costo unitario y total combinado en moneda de la OC
    """

    _name = "report.purchase_cost_report.report_purchase_cost"
    _description = "Purchase Cost Report in Purchase Currency"

    @api.model
    def _get_report_values(self, docids, data=None):
        orders = self.env["purchase.order"].browse(docids)
        report_data = [self._prepare_order_data(order) for order in orders]
        env = self.env
        return {
            "docs": orders,
            "report_data": report_data,
            # formatLang ya no se inyecta automáticamente en Odoo 19
            "formatLang": lambda value, digits=None, currency_obj=None: _formatLang(
                env, value, digits=digits, currency_obj=currency_obj
            ),
        }

    def _prepare_order_data(self, order):
        """Construye el diccionario de datos del reporte para una OC."""
        po_currency = order.currency_id
        company = order.company_id
        company_currency = company.currency_id
        same_currency = po_currency == company_currency

        lines = []
        for pol in order.order_line.filtered(
            lambda l: l.product_id and l.product_id.type in ("product", "consu")
        ):
            # Movimientos de recepción completados
            done_moves = pol.move_ids.filtered(
                lambda m: m.state == "done" and m._is_in()
            )
            received_qty = sum(m._get_valued_qty() for m in done_moves)

            if float_is_zero(received_qty, precision_digits=6):
                continue

            # ── Costo del proveedor ────────────────────────────────────────
            # price_unit en la OC siempre está en la moneda de la OC
            product_unit_cost = pol.price_unit
            product_total_cost = pol.price_unit * received_qty

            # ── Costos en destino ──────────────────────────────────────────
            done_move_ids = set(done_moves.ids)
            pickings = order.picking_ids.filtered(lambda p: p.state == "done")
            landed_costs = self.env["stock.landed.cost"].search(
                [("picking_ids", "in", pickings.ids), ("state", "=", "done")]
            )

            lc_lines = []
            lc_total = 0.0

            for lc in landed_costs:
                # Líneas de ajuste que corresponden a este producto Y a movimientos de esta OC
                adj = lc.valuation_adjustment_lines.filtered(
                    lambda l: l.product_id == pol.product_id
                    and l.move_id.id in done_move_ids
                )
                if not adj:
                    continue

                # Monto en moneda de la compañia (ARS) acumulado en las líneas de ajuste
                amount_company = sum(adj.mapped("additional_landed_cost"))
                if float_is_zero(amount_company, precision_rounding=company_currency.rounding):
                    continue

                # Fecha y moneda de referencia para el TC
                lc_date, lc_ref_currency, amount_ref = self._get_lc_amount_in_ref_currency(
                    lc, amount_company, company_currency
                )

                if same_currency or lc_ref_currency == po_currency:
                    # Si la moneda del comprobante ya es la moneda de la OC,
                    # se usa directamente sin conversión
                    amount_po = amount_ref
                else:
                    amount_po = lc_ref_currency._convert(
                        amount_ref,
                        po_currency,
                        company,
                        lc_date,
                    )

                lc_total += amount_po
                lc_lines.append(
                    {
                        "name": lc.name,
                        "landed_cost": lc,                   # ORM record → usado en wizard
                        "vendor_bill": lc.vendor_bill_id,    # ORM record → usado en wizard y PDF
                        "date": lc_date,
                        "ref_currency": lc_ref_currency,
                        "amount_ref": amount_ref,
                        "amount_po": amount_po,
                    }
                )

            # ── Totales ────────────────────────────────────────────────────
            total_cost = product_total_cost + lc_total
            unit_cost = total_cost / received_qty if received_qty else 0.0

            lines.append(
                {
                    "product": pol.product_id,
                    "description": pol.name,
                    "ordered_qty": pol.product_qty,
                    "received_qty": received_qty,
                    "uom": pol.product_uom_id,
                    "product_unit_cost": product_unit_cost,
                    "product_total_cost": product_total_cost,
                    "lc_lines": lc_lines,
                    "lc_total": lc_total,
                    "total_cost": total_cost,
                    "unit_cost": unit_cost,
                }
            )

        total_product = sum(l["product_total_cost"] for l in lines)
        total_lc = sum(l["lc_total"] for l in lines)
        total_all = sum(l["total_cost"] for l in lines)
        # % de costos en destino sobre el costo del proveedor
        lc_percentage = (total_lc / total_product * 100.0) if total_product else 0.0

        # ── Resumen de Costos en Destino (agrupado por LC, sin repetir por producto) ──
        lc_summary_dict = {}
        for line in lines:
            for lc in line["lc_lines"]:
                key = lc["landed_cost"].id
                if key not in lc_summary_dict:
                    lc_summary_dict[key] = {
                        "landed_cost": lc["landed_cost"],
                        "vendor_bill": lc["vendor_bill"],
                        "date": lc["date"],
                        "ref_currency": lc["ref_currency"],
                        "amount_ref": 0.0,
                        "amount_po": 0.0,
                    }
                lc_summary_dict[key]["amount_ref"] += lc["amount_ref"]
                lc_summary_dict[key]["amount_po"] += lc["amount_po"]

        # Calcular tipo de cambio por LC: 1 {po_currency} = X {ref_currency}
        for lcs in lc_summary_dict.values():
            if (
                lcs["ref_currency"] != po_currency
                and not float_is_zero(lcs["amount_po"],
                                      precision_rounding=po_currency.rounding)
            ):
                lcs["exchange_rate"] = lcs["amount_ref"] / lcs["amount_po"]
            else:
                lcs["exchange_rate"] = 0.0

        lc_summary = sorted(lc_summary_dict.values(), key=lambda x: x["date"] or "")

        return {
            "order": order,
            "currency": po_currency,
            "lines": lines,
            "total_product": total_product,
            "total_lc": total_lc,
            "total_all": total_all,
            "lc_percentage": lc_percentage,
            "lc_summary": lc_summary,
        }

    def _get_lc_amount_in_ref_currency(self, lc, amount_company, company_currency):
        """
        Devuelve (fecha, moneda_referencia, monto_referencia) para convertir
        el costo en destino a la moneda de la OC.

        Si el costo en destino tiene factura de proveedor:
          - usa la moneda y fecha de esa factura
          - recalcula el monto proporcional en la moneda original de la factura
            (más preciso que reconvertir desde moneda compañia)

        Si no tiene factura:
          - usa la moneda de la compañia y la fecha del costo en destino
        """
        if lc.vendor_bill_id and lc.vendor_bill_id.invoice_date:
            bill = lc.vendor_bill_id
            lc_date = bill.invoice_date
            bill_currency = bill.currency_id

            # Proporción del monto de esta(s) línea(s) sobre el total del costo en destino
            # Ambos en moneda compañia → la proporción es válida
            if lc.amount_total and not float_is_zero(lc.amount_total, precision_rounding=company_currency.rounding):
                ratio = amount_company / lc.amount_total
            else:
                ratio = 0.0

            # Monto proporcional en la moneda original de la factura del costo en destino
            bill_amount = bill.amount_untaxed * ratio
            return lc_date, bill_currency, bill_amount
        else:
            lc_date = lc.date or fields.Date.today()
            return lc_date, company_currency, amount_company
