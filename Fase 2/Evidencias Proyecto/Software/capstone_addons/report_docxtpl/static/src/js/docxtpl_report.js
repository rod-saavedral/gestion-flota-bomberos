/** @odoo-module **/

import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";

export function makeReportUrls(action) {
    console.log("makeReportUrls", action)
    let reportUrls = "report/docxtpl/" + action.report_name;

    if (
        action.data === undefined ||
        action.data === null ||
        (typeof action.data === "object" &&
            Object.keys(action.data).length === 0)
    ) {
        if (action.context.active_ids) {
            let activeIDsPath = "/" + action.context.active_ids.join(",");
            reportUrls += activeIDsPath;
        }
    } else {
        let serializedOptionsPath =
            "?options=" + encodeURIComponent(JSON.stringify(action.data));
        serializedOptionsPath +=
            "&context=" + encodeURIComponent(JSON.stringify(action.context));
        reportUrls += serializedOptionsPath;
    }
    return reportUrls;
}

export const reportDocxtpl = async function (action, options, env) {
    if (action.report_type !== "docxtpl") return null;
    console.log("reportDocxtpl", action, options, env)
    const url = makeReportUrls(action);
    env.services.ui.block();
    try {
        await download({
            url: "/report/download",
            data: {
                data: JSON.stringify([url, action.report_type]),
                context: JSON.stringify(action.context),
            },
        });
    } finally {
        env.services.ui.unblock();
    }
    return { type: "ir.actions.act_window_close" }

};
registry
    .category("ir.actions.report handlers")
    .add("docxtlp_report", reportDocxtpl);
