# Purchase Cost Report in Purchase Currency

**Odoo 19.0** | [Aceleradora LA](https://aceleradora.la) | License: LGPL-3

---

## What it does

When your company buys in a foreign currency (e.g. EUR) but operates in a local currency (e.g. ARS), Odoo's standard reports show all costs converted to the company currency. This module adds a valuation report that shows the **real unit and total cost of each received product in the purchase order currency**, including all landed costs (freight, customs, insurance) converted at the exchange rate of the date of each cost invoice.

Access it in one click from the **Purchase Order** or the **Vendor Bill**.

---

## Features

- **Costs in purchase currency** — vendor unit cost and total directly from the PO line, no manual conversion
- **Landed costs at correct exchange rate** — each landed cost is converted to the PO currency using the rate at the invoice date of that landed cost
- **Multi-currency landed costs** — handles LC invoices in ARS, EUR, USD, or any currency
- **Import cost %** — total landed costs as a % of vendor cost, shown prominently
- **On-screen interactive wizard** with 3 tabs:
  - Product summary
  - Landed cost summary (with clickable links to LCs and their invoices)
  - Full detail per product × landed cost
- **PDF report** accessible from the Purchase Order print menu
- **Smart button visibility** — shown only on orders/invoices with storable products

---

## Report columns

| Column | Description |
|--------|-------------|
| Product | Product name |
| Ordered / Received Qty | Quantities from PO and receipts |
| Vendor Unit Cost | `price_unit` from PO line in PO currency |
| Vendor Total Cost | `price_unit × received_qty` in PO currency |
| Landed Costs | Sum of all LCs allocated to this product, converted to PO currency |
| **Total Unit Cost** | `(Vendor + Landed) / received_qty` in PO currency |
| **Total Cost** | `Vendor + Landed` in PO currency |
| Import Cost % | `Total Landed / Total Vendor × 100` |

---

## Multi-currency conversion logic

| Scenario | Conversion |
|----------|-----------|
| LC invoice in same currency as PO | No conversion — used directly |
| LC invoice in third currency (e.g. ARS freight on EUR purchase) | `invoice_currency → PO_currency` at LC invoice date |
| LC without vendor bill | `company_currency → PO_currency` at LC date |

---

## Installation

1. Copy the module to your Odoo addons path
2. Update module list (`Settings → Technical → Update Module List`)
3. Install **Purchase Cost Report in Purchase Currency**

**Dependencies** (auto-installed): `purchase_stock`, `stock_landed_costs`

---

## Configuration

No configuration required. The "Valuación" button appears automatically on:
- Purchase Orders in state `Purchase Order` or `Done` with at least one storable product
- Vendor Bills linked to a PO with storable products

---

## Usage

1. Open a confirmed Purchase Order (or its vendor bill)
2. Click the **"Valuación"** smart button
3. Review costs in the interactive wizard
4. Click **"Imprimir PDF"** to generate the report

---

## Changelog

### 19.0.1.0.0
- Initial release for Odoo 19.0
- On-screen wizard with 3 tabs (product summary, LC summary, detail)
- PDF report with product table and LC summary grid
- Import cost percentage
- Smart button visibility based on storable products

---

## Support

- 📧 [info@aceleradora.la](mailto:info@aceleradora.la)
- 🌐 [aceleradora.la](https://aceleradora.la)
- 🐛 [GitHub Issues](https://github.com/aceleradora-la/purchase_cost_report/issues)

---

## License

[LGPL-3](https://www.gnu.org/licenses/lgpl-3.0.html)
