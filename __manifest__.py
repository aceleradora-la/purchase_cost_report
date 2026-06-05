{
    "name": "Purchase Cost Report in Purchase Currency",
    "version": "19.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": (
        "Valuation report for purchase receptions in the purchase currency, "
        "including landed costs converted at the exchange rate of each cost date."
    ),
    "author": "Aceleradora LA",
    "website": "https://aceleradora.la",
    "maintainer": "Aceleradora LA",
    "support": "info@aceleradora.la",
    "depends": [
        "purchase_stock",
        "stock_landed_costs",
    ],
    "data": [
        "security/ir.model.access.csv",
        "report/purchase_cost_report_template.xml",
        "views/purchase_cost_report_wizard_views.xml",
        "views/purchase_order_views.xml",
        "views/account_move_views.xml",
    ],
    "images": [
        "static/description/banner.png",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
    "license": "LGPL-3",
}
