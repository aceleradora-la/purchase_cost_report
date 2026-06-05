# Images needed for apps.odoo.com

Place the following files in this directory before publishing:

## Required

- **icon.png** — 128×128 px, PNG with transparency. App icon shown in the store listing.
- **banner.png** — 1380×320 px. Wide banner shown at the top of the app page.
  Referenced in __manifest__.py under `images`.

## Recommended (screenshots)

Name them screenshot_1.png, screenshot_2.png, etc. and reference in index.html <img> tags.
Suggested screenshots:

1. `screenshot_wizard_summary.png` — Wizard open on a PO, Tab "Resumen por Producto"
2. `screenshot_wizard_lc_summary.png` — Tab "Resumen Costos en Destino" with landed cost links
3. `screenshot_pdf.png` — PDF report preview showing main table + LC summary grid
4. `screenshot_po_button.png` — PO form with the "Valuación" smart button visible
5. `screenshot_bill_button.png` — Vendor bill with the "Valuación OC" smart button visible

## Icon design suggestion

Colors: #1a6496 (blue) on white background
Symbol: currency sign (€/$) + document or chart icon
