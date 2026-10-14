=============
Overview
=============

* o: record
* user: current user
* o_date: function format field date
* o_datetime: function format field datetime
* o_monetary: function format field monetary
* o_selection: function format field selection
* o_html: function format field html
* o_float: funtion format field float
* o_image: funtion print image (support field binary(image))
* o_count: funtion count field o2m, m2m
* o_qrcode: function print qrcode (support field char)
* o_barcode: self._format_barcode (support field char)


Field Char
----------
* Example: 
    * {{o.name}}
    * {{o_qrcode(o.website, width=20, height=20)}}   
    * {{o_barcode(o.vat, width=200, height=40, humanreadable=True, quiet=True)}}
    * Ref function barcode in model ir.actions.report

Field Date
----------
* Example: 
    * {{o_date(o.order_date, date_format='full', lang_code='en')}}
* Parameters:
    * date_format: one of “full”, “long”, “medium”, or “short”, or a custom date/time pattern
    * lang_code: a Locale object or a locale identifier

Field Datetime
--------------
* Example: 
    * {{o_datetime(o.create_date, date_format='long', tz='UTC', lang_code='en')}}
* Parameters:
    * dt_format: one of “full”, “long”, “medium”, or “short”, or a custom date/time pattern
    * tz: the timezone to apply to the time for display
    * lang_code: a Locale object or a locale identifier

Field Monetary
--------------
* Example: 
    * {{o_monetary(o.amount_total, currency_obj=o.currency_id, digits=2, no_break_space=True)}}
* Parameters:
    * currency_obj: object currency
    * digits: default currency_obj.decimal_places (optional)
    * no_break_space: default True (optional)

Field Selection
--------------
* Example: 
    * {{o_selection(o.state, field_name='state')}}
* Parameters:
    * field_name: technology field name

Field Html
--------------
* Example: 
    * {{o_html(o.note)}}

Field Float
--------------
* Example: 
    * {{o_float(o.price_unit)}}
* Parameters:
    * precision_digits: number of fractional digits to round to
    * precision_rounding: decimal number representing the minimum non-zero value at the desired precision (for example, 0.01 for a 2-digit precision)
    * rounding_method: the rounding method used 'HALF-UP', 'UP' or 'DOWN' the first one rounding up to the closest number with the rule that number>=0.5 is rounded up to 1, the second always rounding up and the latest one always rounding down

Field Binary
--------------
* Example: 
    * {{o_image(o.partner.image_1920, width=20, height=20)}}
* Parameters:
    * width: default=15 (optional)
    * height: default=15 (optional)
    * no_break_space: optional, default True

Field One2many, Many2many
------------------------
* Example: 
    * {%tr for i, line in o_count(o.order_line, start=1) %}
* Parameters:
    * start: default=1 (optional)

Author & Maintainer
-------------------
* This module is maintained by the Lazydoo <luuthinh2705@gmail.com>