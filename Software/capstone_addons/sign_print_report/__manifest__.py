# -*- coding: utf-8 -*-
#################################################################################
# Author      : CFIS (<https://www.cfis.store/>)
# Copyright(c): 2017-Present CFIS.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://www.cfis.store/>
#################################################################################

{
    "name": "Digital Signature | Sign Print Report | Sign any Report | Sign any Document | Sign PDF | Sign Document",
    "summary": """This module allows users of Odoo to Place Coordinates on any 
        model and select a report or upload a PDF file. Users can include their 
        name, phone number, email address, company name, and signature.""",
    "version": "18.0",
    "description": """
        This module allows users of Odoo to Place Coordinates on any model and select a report or upload a PDF file. Users can include their name, phone number, email address, company name, and signature.
        Digital Signature
        Sign Print Report
        Sign any Report
    """,    
    "author": "CFIS",
    "maintainer": "CFIS",
    "license" :  "Other proprietary",
    "website": "https://www.cfis.store",
    "images": ["images/sign_print_report.png"],
    "category": "Website",
    "depends": [
        "base",
        "web",
    ],
    "data": [
        "views/assets.xml",
        "views/res_partner_views.xml",
    ],
    "assets": {
        'sign_print_report.assets_pdf_iframe': [            
            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/lib/bootstrap/scss/_functions.scss',
            'web/static/src/scss/functions.scss',
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/lib/bootstrap/scss/_variables-dark.scss',
            'web/static/lib/bootstrap/scss/_maps.scss',
            'web/static/lib/bootstrap/scss/vendor/_rfs.scss',
            'web/static/lib/bootstrap/scss/mixins/_deprecate.scss',
            'web/static/lib/bootstrap/scss/mixins/_utilities.scss',
            'web/static/lib/bootstrap/scss/mixins/_breakpoints.scss',
            'web/static/lib/bootstrap/scss/mixins/_grid.scss',
            'web/static/lib/bootstrap/scss/_utilities.scss',
            'web/static/lib/bootstrap/scss/_grid.scss',
            'web/static/src/scss/bs_mixins_overrides.scss',
            'web/static/lib/bootstrap/scss/utilities/_api.scss',
            'web/static/src/scss/utils.scss',
            'web/static/src/scss/primary_variables.scss',
            'web/static/src/scss/secondary_variables.scss',
            'sign_print_report/static/src/css/*.css',
        ],
        "web.assets_backend": [
            "/sign_print_report/static/src/js/*.*",
            "/sign_print_report/static/src/css/*.css",
        ],
    },  
    "installable": True,
    "application": True,
    "price"                 :  130.00,
    "currency"              :  "EUR",
    "pre_init_hook"         :  "pre_init_check",
}
