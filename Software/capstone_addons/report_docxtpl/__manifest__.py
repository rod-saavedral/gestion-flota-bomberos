# -*- coding:utf-8 -*-
{
    "name": "Report Docx",
    "summary": "Export data all objects odoo to Microsoft Office. output files docx, pdf",
    "version": "18.0.1.2",
    "category": "Reporting",
    "license": "OPL-1",
    "author": "Lazydoo",
    "price": 29.00,
    "live_test_url": "https://lazydoo.net",
    "currency": "USD",
    "depends": [
        "base",
        "web",
    ],
    "data": [
        "data/docxtpl_data.xml",
        "security/ir.model.access.csv",
        "views/doc_template_view.xml",
    ],
    "external_dependencies": {
        "python": [
            "docxcompose",
            "docxtpl",
        ],
        "deb": ["libreoffice"],
    },
    "assets": {
        "web.assets_backend": [
            "report_docxtpl/static/src/js/docxtpl_report.js",
            "report_docxtpl/static/src/js/form_controller.js",
        ],
    },
    "images": [
        "static/description/banner.png",
        "static/description/theme_screenshot.png",
    ],
    "installable": True,
}
