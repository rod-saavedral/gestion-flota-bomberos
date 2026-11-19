{
    "name": "Bomberos - Flota",
    "summary": "Registro y estado operativo de vehículos de emergencia",
    "version": "18.0.1.0.0",
    "category": "Operations",
    "license": "LGPL-3",
    "depends": ["bomberos_base"],
    "data": [
        "security/ir.model.access.csv",
        "security/rules.xml",
        "views/vehicle_views.xml",
        "views/company_views.xml",
        "views/menus.xml",
    ],
    "demo": ["demo/vehicle_demo.xml"],
    "application": False,
    "installable": True,
}
