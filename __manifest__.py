{
    "name": "Purchase Cost Report in Purchase Currency",
    "version": "19.0.1.0.0",
    "category": "Purchase",
    "summary": "Reporte de valuación de recepciones en moneda de la orden de compra, incluyendo costos en destino convertidos al TC de la fecha del costo.",
    "author": "Aceleradora LA",
    "website": "https://aceleradora.la",
    "depends": [
        "purchase_stock",
        "stock_landed_costs",
    ],
    "data": [
        "report/purchase_cost_report_template.xml",
        "views/purchase_cost_report_wizard_views.xml",
        "views/purchase_order_views.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
    "license": "AGPL-3",
}
