# -*- coding:utf-8 -*-
import base64
import io
import logging
import time

import qrcode
import requests
from docx.shared import Mm
from docxtpl import InlineImage, R
from odoo.tools import float_round, groupby, mail, misc

logger = logging.getLogger(__name__)


class ParserContext(object):
    def __init__(self, model, doc):
        self.model = model
        self.env = model.env
        self.doc = doc

        self.localcontext = {
            "user": self.env.user,
            "lang": self.env.lang,
            "o_monetary": self._format_monetary,
            "o_date": self._format_date,
            "o_datetime": self._format_datetime,
            "o_selection": self._format_selection,
            "time": time,
            "o_html": mail.html2plaintext,
            "o_float": self._float_round,
            "merge_row": self._merge_row,
            "o_image": self._format_image,
            "o_image_url": self._format_image_url,
            "o_count": self._format_count,
            "o_qrcode": self._format_qrcode,
            "o_barcode": self._format_barcode,
            "page_break": R("\f"),
            "o_groupby": self._groupby,
            "o_str": self._str
        }

    def _merge_row(self, check_merge, bg="FFFFFF"):
        if not check_merge:
            return bg + '<w:vMerge w:val="restart"'
        else:
            return bg + '<w:vMerge w:val="continue"'

    def _format_monetary(
        self,
        value,
        currency_obj,
        digits=None,
        no_break_space=True,
    ):
        formatted_value = misc.formatLang(
            self.env,
            value,
            digits=digits,
            grouping=True,
            monetary=True,
            dp=False,
            currency_obj=currency_obj,
        )
        if currency_obj and currency_obj.symbol and no_break_space:
            parts = []
            if currency_obj.position == "after":
                parts = formatted_value.rsplit(" ", 1)
            elif currency_obj and currency_obj.position == "before":
                parts = formatted_value.split(" ", 1)
            if parts:
                formatted_value = "\N{NO-BREAK SPACE}".join(parts)
        return formatted_value

    def _format_selection(self, value, field_name):
        return dict(self.model._fields[field_name].get_description(self.env)["selection"]).get(value, '')

    def _format_date(self, value, date_format=False, lang_code=False):
        return misc.format_date(
            self.env, value, lang_code=lang_code, date_format=date_format
        )

    def _format_datetime(self, value, dt_format="medium", tz=False, lang_code=False):
        return misc.format_datetime(
            self.env, value, tz=tz, dt_format=dt_format, lang_code=lang_code
        )

    def _float_round(
        self,
        value,
        precision_digits=None,
        precision_rounding=None,
        rounding_method="HALF-UP",
    ):
        return float_round(
            value,
            precision_digits=precision_digits,
            precision_rounding=precision_rounding,
            rounding_method=rounding_method,
        )

    def _format_image(self, value, width=15, height=15):
        if not value:
            return ""
        return InlineImage(
            self.doc,
            io.BytesIO(base64.b64decode(value)),
            width=Mm(width),
            height=Mm(height),
        )

    def _format_image_url(self, url, width=15, height=15):
        try:
            res = requests.get(url)
            if res.status_code == 200:
                return InlineImage(
                    self.doc,
                    io.BytesIO(res.content),
                    width=Mm(width),
                    height=Mm(height),
                )
            else:
                return ""
        except:
            return ""

    def _format_count(self, records, start=1):
        return enumerate(records, start)

    def _format_qrcode(self, value, width=15, height=15):
        if not isinstance(value, str):
            return ""
        qr_img = io.BytesIO()
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(value)
        qr.make(fit=True)
        qr.make_image().save(qr_img, format="PNG")
        return InlineImage(
            self.doc,
            qr_img,
            width=Mm(width),
            height=Mm(height),
        )

    def _format_barcode(self, value, type='auto', **kwargs):
        if not isinstance(value, str):
            return ""
        bar_img = io.BytesIO(self.env['ir.actions.report'].barcode(type, value, **kwargs))
        return InlineImage(
            self.doc,
            bar_img,
        )
    
    def _groupby(self, records, field_name, max_items=0):
        def chunk(lst, n):
            if n <= 0:
                return lst
            
            for i in range(0, len(lst), n):
                yield lst[i: i+n]
        
        res = []
        if not records or not field_name in records._field:
            return res
        
        for key, items in groupby(records, key=lambda r: r[field_name]):
            res += [(key, item) for item in chunk(items, max_items)]
        
        return res
    
    def _str(self, value):
        return str(value) if value else None
