{
    "name": "Bomberos - Base",
    "summary": "Compañías y perfiles para el sistema de flota de emergencia",
    "version": "18.0.1.0.0",
    "category": "Operations",
    "license": "LGPL-3",
    "depends": ["base", "web"],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "security/rules.xml",
        "views/company_views.xml",
        "views/res_users_views.xml",
        "views/menus.xml",
    ],
    "demo": ["demo/company_demo.xml"],
    "application": True,
    "installable": True,
}
