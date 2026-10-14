# -*- coding:utf-8 -*-

import json
import mimetypes

from werkzeug import exceptions
from werkzeug.urls import url_decode

from odoo import http
from odoo.http import request, route, serialize_exception, content_disposition
from odoo.tools import html_escape

from odoo.addons.web.controllers import report


class ReportController(report.ReportController):
    @route()
    def report_routes(self, reportname, docids=None, converter=None, **data):
        if converter != "docxtpl":
            return super(ReportController, self).report_routes(
                reportname=reportname, docids=docids, converter=converter, **data
            )
        context = dict(request.env.context)

        if docids:
            docids = [int(i) for i in docids.split(",")]
        if data.get("options"):
            data.update(json.loads(data.pop("options")))
        if data.get("context"):
            data["context"] = json.loads(data["context"])
            if data["context"].get("lang"):
                del data["context"]["lang"]
            context.update(data["context"])

        ir_action = request.env["ir.actions.report"]
        action_docxtpl_report = ir_action.get_docxtpl_from_report_name(
            reportname).with_context(context)
        if not action_docxtpl_report:
            raise exceptions.HTTPException(
                description="docxtpl action report not found for report_name "
                "%s" % reportname
            )
        filename, filetype, res = action_docxtpl_report._render(reportname, docids, data)
        content = res.read()
        if not filename.endswith(filetype):
            filename = "{}.{}".format(filename, filetype)
        content_type = mimetypes.guess_type("x." + filetype)[0]
        http_headers = [
            ("Content-Type", content_type),
            ("Content-Length", len(content)),
            ("Content-Disposition", content_disposition(filename)),
        ]
        return request.make_response(content, headers=http_headers)

    @route()
    def report_download(self, data, context=None):
        requestcontent = json.loads(data)
        url, report_type = requestcontent[0], requestcontent[1]

        if "docxtpl" not in report_type:
            return super(ReportController, self).report_download(data, context=context)
        try:
            reportname = url.split("report/docxtpl/")[1].split("?")[0]
            docids = None
            if "/" in reportname:
                reportname, docids = reportname.split("/")

            if docids:
                # Generic report:
                response = self.report_routes(
                    reportname, docids=docids, converter="docxtpl"
                )
            else:
                # Particular report:
                # decoding the args represented in JSON
                data = list(url_decode(url.split("?")[1]).items())
                response = self.report_routes(
                    reportname, converter="docxtpl", **dict(data)
                )
            response.set_cookie("fileToken", context)
            return response
        except Exception as e:
            se = serialize_exception(e)
            error = {"code": 200, "message": "Odoo Server Error", "data": se}
            return request.make_response(html_escape(json.dumps(error)))