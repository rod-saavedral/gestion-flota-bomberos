/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useRef, Component, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

export class SignPrintReportSelection extends Component {
    setup() {
        this.title = _t("Select Sign Report");
        this.selectReportCheckRef = useRef("is_select_report");
        this.uploadFileCheckRef = useRef("is_upload_file");
        this.selectReportContainerRef = useRef("select_report_container");
        this.uploadFileContainerRef = useRef("upload_file_container");
        this.uploadNewFileNameRef = useRef("new_uploaded_file_name");
        this.selectedReportRef = useRef("selected_report");
        this.signButtonRef = useRef("sign_button");

        this.imageRef = useRef("image");
        this.selectRef = useRef("select");
        this.state = {
            rowid : 1,
            uploaded_file : false,
        }
        this.notificationService = useService("notification"); 
    }
    get options() {
        var partners = []
        for (var i = 0; i < this.props.partnerData.length; i++) {
            var value = {
                id: this.props.partnerData[i].id,
                name: this.props.partnerData[i].name + ' - ' +  this.props.partnerData[i].email,
            }
            partners.push(value)
        }
        return partners;
    }
    onSelectReportCheck(){
        var upload_file = this.uploadFileCheckRef.el;
        upload_file.checked = false;

        var select_report = this.selectReportCheckRef.el;
        if(select_report.checked){
            this.selectReportContainerRef.el.style.display = '';
            this.uploadFileContainerRef.el.style.display = 'none';
        }
    }
    onUploadFileCheck(){
        var select_report = this.selectReportCheckRef.el;
        select_report.checked = false;

        var upload_file = this.uploadFileCheckRef.el;
        if(upload_file.checked){
            this.uploadFileContainerRef.el.style.display = '';
            this.selectReportContainerRef.el.style.display = 'none';
        }
    }
    onClickUploadFile(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const self = this;
        
        const newPdfInput = document.createElement('input');
        newPdfInput.type = 'file';
        newPdfInput.name = 'files[]';
        newPdfInput.accept = 'application/pdf';
    
        newPdfInput.addEventListener('change', async (e) => {
            const files = newPdfInput.files;
            newPdfInput.remove();
            for (const file of files) {
                if (file) {
                    self.uploadNewFileNameRef.el.innerHTML = file.name;
                    self.state.uploaded_file = file;
                }
            }
        });
        
        newPdfInput.click();
    }    
    close() {
        this.props.close && this.props.close();
    }
    async onClickConfirm(ev){
        ev.preventDefault();
        ev.stopPropagation();

        var self = this;
        self.signButtonRef.el.disabled = true;

        var select_report = self.selectReportCheckRef.el;
        var upload_file = self.uploadFileCheckRef.el;
        if (select_report.checked) {
            const reportSelect = this.selectedReportRef.el;
            const report_name = reportSelect.querySelector(':checked');
        
            if (!report_name) {
                reportSelect.classList.add('highlight_alert');
            } else {
                reportSelect.classList.remove('highlight_alert');
            }
        
            if (report_name) {
                const data = await this._getReportData(report_name.getAttribute('report_name'));
                if (data) {
                    this._sendReportData(data);
                } else {
                    this.notificationService.add(_t("Report file is not supported, Please try again."), { type: "danger" });
                }
            }
        }        
        else if(upload_file.checked){
            var data = self.state.uploaded_file;
            if (data != false){
                if (data) {
                    var reader = new FileReader();
                    reader.onload = async function () {
                        var data = this.result
                        data = data.split(',')[1];
                        if (data){
                            var data = await self._getUploadedData(data);
                            self._sendReportData(data);
                        }else{
                            self.notificationService.add(_t("Uploaded file is not supported, Please upload again."),{type: "danger",});
                        }
                    }
                    reader.readAsDataURL(data);
                }
            }else{
                var fileNameTag = self.uploadNewFileNameRef.el;
                fileNameTag.innerHTML = '<span style="color:red;">Please upload a pdf file to sign.</span>'
            }

        }
        else{
            self.notificationService.add(_t("Please select report or upload file."),{type: "danger",});
        }
    }

    async _getReportData(report_name) {
        var self = this;
        var defs = [];

        var active_model = self.props.resModel;
        var active_id = self.props.resId;
        
        defs.push(await rpc("/sign_print_report/get_report_data/",{
            active_id: active_id,
            active_model: active_model,
            report_name: report_name,
        }));
        
        return Promise.all(defs).then(async function (data) {
            var base64 = data;
            const binStr = atob(base64);
            const len = binStr.length;
            const arr = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                arr[i] = binStr.charCodeAt(i);
            }
            var bdata = new Blob([arr], { type: 'application/octet-stream' });
            return bdata;
        });
    }
    async _getUploadedData(data){
        var self = this;
        var base64 = data;
        const binStr = atob(base64);
        const len = binStr.length;
        const arr = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            arr[i] = binStr.charCodeAt(i);
        }
        var bdata = new Blob([arr], { type: 'application/octet-stream' });
        return bdata
    }

    async _sendReportData(data) {
        var self = this;        
        self.props.openSingReportDialog(data);
        self.signButtonRef.el.disabled = false;
        self.props.close && self.props.close();
    }
}
SignPrintReportSelection.components = { Dialog };
SignPrintReportSelection.template = "sign_print_report.SignPrintReportSelection";
SignPrintReportSelection.defaultProps = {
    resId: false,
    resModel:false,
    reportData: [],
    partnerData: [],
};