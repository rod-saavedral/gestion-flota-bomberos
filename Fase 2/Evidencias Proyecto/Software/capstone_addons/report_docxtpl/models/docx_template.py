# -*- coding:utf-8 -*-

import io
import base64
import tempfile
import os
import subprocess
import logging
from contextlib import closing
import pkg_resources
from zipfile import ZipFile
from datetime import datetime

from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval, time
from odoo.tools.misc import find_in_path

from ._parser_context import ParserContext

try:
    from docxtpl import DocxTemplate
    from docx.shared import Mm
    from docxcompose.composer import Composer
    from docx import Document
    from docx.text.run import *
except ImportError as e:
    raise UserError(_("Please install library docxtpl."))


DOCXTPL_CONVERSION_COMMAND_PARAMETER = "docxtpl.conversion_command"

_logger = logging.getLogger(__name__)


class DocxTemplateModel(models.Model):
    _name = "docx.template"
    _description = "Docx Template"

    name = fields.Char(string="Name", required=True)
    type = fields.Selection(
        [("report", "Report"), ("header", "Header/Footer")],
        string="Type",
        required=True,
        default="report",
    )
    use_header = fields.Boolean(string="Use Header/Footer")
    header_id = fields.Many2one("docx.template", string="Header/Footer")
    docx_template_data = fields.Binary(string="Template")
    docx_template_name = fields.Char(string="Template name")
    module = fields.Char(
        "Module", help="The implementer module that provides this report", readonly=True
    )
    docx_template_path = fields.Char(string="Template Path", readonly=True)
    print_report_name = fields.Char(string="Report name")
    model_id = fields.Many2one("ir.model", string="Model", ondelete="cascade")
    report_ids = fields.One2many("ir.actions.report", "docxtpl_id", string="#")
    report_id = fields.Many2one(
        "ir.actions.report", compute="_compute_report", store=True
    )
    id_for_button = fields.Integer("ID For Button", related="report_id.id", store=True)
    is_publish = fields.Boolean(string="#")
    format_output = fields.Selection(
        [("docx", "Docx"), ("pdf", "Pdf")],
        string="Format Output",
        required=True,
        default="docx",
    )
    lo_bin_path = fields.Char(string="Path libreoffice", compute="_compute_lo_bin_path")
    merge_or_zip = fields.Selection(
        [("merge", "Merge File"), ("zip", "Zip File")], string="Merge Or Zip"
    )
    direct_print = fields.Boolean(string="Direct Print")

    @api.onchange("type")
    def onchange_type(self):
        self.model_id = False
        self.use_header = False
        self.header_id = False
        self.print_report_name = False

    @api.model
    def _get_lo_bin(self):
        lo_bin = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(DOCXTPL_CONVERSION_COMMAND_PARAMETER, "libreoffice")
        )
        try:
            lo_bin = find_in_path(lo_bin)
        except IOError:
            lo_bin = None
        return lo_bin

    def _compute_lo_bin_path(self):
        lo_bin = self._get_lo_bin()
        for rec in self:
            rec.lo_bin_path = lo_bin

    @api.depends("report_ids")
    def _compute_report(self):
        for each in self:
            if each.report_ids:
                each.report_id = each.report_ids[0]
            else:
                each.report_id = False

    def action_publish(self):
        if not self.is_publish and self.type == "report":
            self.env["ir.actions.report"].create(
                {
                    "name": self.name,
                    "type": "ir.actions.report",
                    "report_name": self.name,
                    "print_report_name": self.print_report_name,
                    "report_type": "docxtpl",
                    "model": self.model_id.model,
                    "binding_model_id": self.model_id.id,
                    "binding_type": "report",
                    "docxtpl_id": self.id,
                }
            )
            self.write({"is_publish": True})

    def action_unpublish(self):
        self.report_id.unlink()
        self.write({"is_publish": False})

    def unlink(self):
        self.report_id.unlink()
        return super(DocxTemplateModel, self).unlink()

    # ////////////////////// render /////////////////////////////////////////////
    def _is_valid_template_path(self, path):
        """Check if the path is a trusted path for Docx templates."""
        real_path = os.path.realpath(path)
        root_path = tools.config.get_misc("report_docx", "root_tmpl_path")
        if not root_path:
            _logger.warning(
                "You must provide a root template path into odoo.cfg to be "
                "able to use docx template configured with an absolute path "
                "%s",
                real_path,
            )
            return False
        is_valid = real_path.startswith(root_path + os.path.sep)
        if not is_valid:
            _logger.warning(
                "Docx template path is not valid. %s is not a child of root " "path %s",
                real_path,
                root_path,
            )
        return is_valid

    def _get_template_from_path(self):
        """Return the template from the path to root of the module if specied
        or an absolute path on your server
        """

        if not self.docx_template_path or not self.module:
            raise ValidationError(
                _("docx_template_path or module of this record is None")
            )

        flbk_filename = pkg_resources.resource_filename(
            "odoo.addons.%s" % self.module, self.docx_template_path
        )

        try:
            with open(flbk_filename, "rb") as tmpl:
                return tmpl.read()
        except:
            raise ValidationError("Error when trying to get template from path.")

    def render(self, res_ids, data):
        Model = self.env[self.model_id.model]
        if res_ids:
            records = Model.browse(res_ids)
            filename = self.gen_docx_name_report(res_ids)

        file = False
        if self.docx_template_data:
            file = io.BytesIO(base64.b64decode(self.docx_template_data))
        else:
            file = io.BytesIO(self._get_template_from_path())

        if not file:
            raise UserError(_("Template Error. Please check template file"))

        doc = DocxTemplate(file)

        Model = self.env[self.model_id.model]
        files = []
        zip_filenames = []
        records = Model.browse(res_ids)
        context = ParserContext(Model, doc).localcontext
        for record in records:
            output = io.BytesIO()
            context.update({"o": record})

            doc.render(context, autoescape=True)
            doc.save(output)

            # merge col in table(with text merge_col_r or merge_col_l)
            output = self.docx_table_merge_col(output)

            files.append(output)
            zip_filenames.append(self.gen_docx_name_report(record.ids))

        if self.merge_or_zip == "merge" or len(files) == 1:
            if self.format_output == "docx":
                return filename, "docx", self.combine_all_docx(files)
            else:
                docx_file = self.combine_all_docx(files)
                pdf_path = self.convert_to_pdf(docx_file)
                f = open(pdf_path, "rb")
                return filename, "pdf", f
        else:
            zip_out = io.BytesIO()
            zip_file = ZipFile(zip_out, "w")

            if self.format_output == "docx":
                for zip_name, file in zip(zip_filenames, files):
                    file.seek(0)
                    data_record = file.read()
                    zip_file.writestr(f"{zip_name}.docx", data_record)
            else:
                for zip_name, file in zip(zip_filenames, files):
                    file.seek(0)
                    pdf_path = self.convert_to_pdf(file)
                    f_pdf = open(pdf_path, "rb")
                    data_record = f_pdf.read()
                    zip_file.writestr(f"{zip_name}.pdf", data_record)

            zip_file.close()
            zip_out.seek(0)
            now = datetime.now().timestamp()
            return f"{filename}-{now}", "zip", zip_out

    def docx_table_merge_col(self, file):
        doc = Document(file)

        def delete_paragraph(paragraph):
            p = paragraph._element
            p.getparent().remove(p)
            p._p = p._element = None

        for table in doc.tables:
            for row_idx in range(0, len(table.rows)):
                for col_idx in range(0, len(table.columns)):
                    try:
                        current_cell = table.cell(row_idx, col_idx)
                    except:
                        current_cell = False

                    if not current_cell:
                        continue

                    if current_cell.text == "merge_col_l" and col_idx != 0:
                        merge_col_idx = col_idx - 1
                    elif current_cell.text == "merge_col_r" and col_idx != (
                        len(table.columns) - 1
                    ):
                        merge_col_idx = col_idx + 1
                    else:
                        continue

                    for p in current_cell.paragraphs:
                        delete_paragraph(p)
                    current_cell.add_paragraph()

                    table.cell(row_idx, merge_col_idx).merge(current_cell)

        output = io.BytesIO()
        doc.save(output)
        output.seek(0)
        return output

    def combine_all_docx(self, files):            
        number_of_section = len(files)
        header_file = False
        master = Document(files[0])

        # prepare header
        if self.use_header and self.header_id:
            header_file = self.header_id.render_header_footer()

        if number_of_section > 1:
            master.add_page_break()

        if header_file:
            composer = Composer(Document(header_file))
            composer.append(master)
        else:
            composer = Composer(master)

        for i in range(1, number_of_section):
            doc_append = Document(files[i])
            if i <= number_of_section - 1:
                doc_append.add_page_break()
            composer.append(doc_append)

        output = io.BytesIO()
        composer.save(output)
        output.seek(0)
        return output

    def gen_docx_name_report(self, res_ids):
        self.ensure_one()
        if self.print_report_name and not len(res_ids) > 1:
            obj = self.env[self.model_id.model].browse(res_ids)
            return safe_eval(self.print_report_name, {"object": obj, "time": time})
        return "{}.{}".format(self.name, self.format_output)

    def _convert_report_cmd(self, result_path, user_installation=None):
        if not self.lo_bin_path:
            raise RuntimeError(
                _(
                    "Libreoffice runtime not available. Please contact your administrator."
                )
            )

        cmd = [self.lo_bin_path, "--headless", "--convert-to", "pdf", result_path]
        if user_installation:
            cmd.append("-env:UserInstallation=file:%s" % user_installation)
        return cmd

    def convert_to_pdf(self, file):
        # with tempfile.TemporaryDirectory() as tmp_user_installation:
        #     command = self._convert_report_cmd
        self.ensure_one()
        result_fd, result_path = tempfile.mkstemp(
            suffix=".docx", prefix="report.docx.tmp"
        )
        with closing(os.fdopen(result_fd, "wb+")) as out_stream:
            out_stream.write(file.read())
            out_stream.seek(0)

        with tempfile.TemporaryDirectory() as tmp_user_installation:
            command = self._convert_report_cmd(
                result_path,
                user_installation=tmp_user_installation,
            )
            _logger.info("Running command %s", command)
            output = subprocess.check_output(command, cwd=os.path.dirname(result_path))
            _logger.info("Output was %s", output)
            self._cleanup_tempfiles([result_path])
            result_path, result_filename = os.path.split(result_path)
            result_path = os.path.join(
                result_path, "%s.%s" % (os.path.splitext(result_filename)[0], "pdf")
            )

        return result_path

    @api.model
    def _cleanup_tempfiles(self, temporary_files):
        for temp in temporary_files:
            try:
                os.unlink(temp)
            except OSError:
                _logger.error("Error when trying to remove file %s" % temp)

    def render_header_footer(self):
        result = io.BytesIO()
        file = False
        if self.docx_template_data:
            file = io.BytesIO(base64.b64decode(self.docx_template_data))
        else:
            file = io.BytesIO(self._get_template_from_path())

        if not file:
            raise UserError("Template Error. Please check template file")

        doc = DocxTemplate(file)
        Model = self.env[self.model_id.model]
        context = ParserContext(Model, doc).localcontext

        doc.render(context, autoescape=True)
        doc.save(result)
        result.seek(0)
        return result
