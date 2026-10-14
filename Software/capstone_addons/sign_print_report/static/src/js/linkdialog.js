/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { onMounted, useState, useRef, Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class LinkDialog extends Component {
    setup() {
        this.title = _t("Download Signed Document");
        this.linkRef = useRef("link");
        

        onMounted(async () => {
            this.linkRef.el.append(this.props.downloadLink);
        });  

    }
    close() {
        this.props.close && this.props.close();
    }
}
LinkDialog.components = { Dialog };
LinkDialog.template = "sign_print_report.LinkDialog";
LinkDialog.defaultProps = {
    downloadLink : String,
};