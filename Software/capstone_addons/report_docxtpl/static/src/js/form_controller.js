/** @odoo-module **/

import { makeReportUrls } from "./docxtpl_report";
import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

import {
    useExternalListener,
} from "@odoo/owl";

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        useExternalListener(window, "keydown", this.direct_print)
    },

    direct_print: async function (ev) {
        if ((ev.ctrlKey || ev.metaKey) && (ev.key == "p" || ev.charCode == 16 || ev.charCode == 112 || ev.keyCode == 80)) {
            let directPrintReport = this.props.info.actionMenus.print.find(r => r.direct_print);
            if (directPrintReport) {
                ev.preventDefault();
                const action = await this.orm.call(
                    "ir.actions.report",
                    "report_action",
                    [directPrintReport.id, [this.props.resId]],
                    { config: false },
                );
                const url = makeReportUrls(action);
                const win = window.open(url, "_blank");
                if (!win) {
                    window.location.href = url;
                }
            }
        }
    }
});
