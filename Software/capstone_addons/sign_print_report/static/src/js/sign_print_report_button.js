/** @odoo-module */

import { FormRenderer } from '@web/views/form/form_renderer';
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { SignPrintReportSelection } from "./sign_print_report_selection"

const { onMounted, onPatched, useEnv , onWillStart} = owl;

patch(FormRenderer.prototype, {
    setup(...args) {
        super.setup(...args);
        this.orm = useService("orm");
        this.action = useService("action");
        this.sign_print_report = useService("sign_print_report");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        
        onWillStart(this.onWillStart);
        onPatched(this._renderSignButton.bind(this));
        onMounted(this._renderSignButton.bind(this));                
    },

    async onWillStart() {
        this.sign_report_data = await this.orm.call("ir.actions.report", "search_read", [[['model', '=', this.props.record.resModel]], ['id', 'name', 'report_name']], {});
    },
    
    _renderSignButton(){
        if (this.sign_report_data.length > 0) {
            const signButtonDiv = document.createElement('div');
            signButtonDiv.classList.add("sign_print_report");
        
            const button = document.createElement('button');
            button.classList.add("btn", "btn-primary");
        
            const icon = document.createElement('i');
            icon.classList.add("fa", "fa-file-signature");
        
            button.appendChild(icon);
            signButtonDiv.appendChild(button);
        
            signButtonDiv.addEventListener('click', this._clickSignButton.bind(this));
            const formSheet = document.querySelector('.o_form_sheet');
            if (this.props.record.resId) {
                formSheet.appendChild(signButtonDiv);
            }
        }        
    },

    async _clickSignButton(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        var self = this;
        var data = this.sign_report_data;
        if (data.length > 0) {
            this._openSingPrintDialog(data);
        }
    },

    _openSingPrintDialog(data) {
        var self = this;
        self.dialog.add(SignPrintReportSelection, {
            resId: self.props.record.resId,
            resModel: self.props.record.resModel,
            reportData: this.sign_report_data,
            partnerData: this.sign_partner_data,
            openSingReportDialog: (data) => this.openSingReportDialog(data),
        });
    },

    async openSingReportDialog(data){      
        var self= this;
        var active_model = self.props.record.resModel;
        var active_id = self.props.record.resId;
        var params = {
            'data': data,
            'name': self.props.record.data.name,
            'active_id': active_id,
            'active_model': active_model,
            'report_name': self.props.record.data.name + '.pdf',
        }
        var action = await self.env.services.action.loadAction(self.action);
        self.sign_print_report.open(params, action)
    }

})

export default FormRenderer;
