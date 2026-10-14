/** @odoo-module **/

import { registry } from "@web/core/registry";
import { EventBus } from "@odoo/owl";

export const signPrintReport = {
    dependencies: ["action"],

    async start(env, {}) {
        const bus = new EventBus();
        
        const state = {
            editedAction: null,
            editedControllerState: null,
            params: null,
        };

        async function open(params, action = false){      
            let controllerState = {};
            if (action) {
                const currentController = action.currentController;
                if (currentController) {
                    action = currentController.action;  
                    const resId = currentController.props.resId;
                    if (resId) {
                        controllerState.resId = resId;
                    }
                }
                state.editedAction = action;
                state.editedControllerState = controllerState;
            }
            state.params = params;
            return env.services.action.doAction("widget_sign_print_report", params);
        }

        async function close(){            
            env.bus.trigger("CLEAR-CACHES");
            if (state.editedAction != null) {
                let actionId = state.editedAction.id;
                const options = {};
                options.clearBreadcrumbs = true;
                options.additionalContext = state.editedAction.context;
                options.viewType = 'form' ;
                if (state.editedControllerState) {
                    options.props = { resId: state.editedControllerState.resId };
                }
                await env.services.action.doAction(actionId,options);
            }else{
                return Promise.resolve().then(function(){
                    window.history.back();
                });
            }
        }

        return {
            bus,
            open,
            close,
            get params() {
                return state.params;
            },
        }
    }
}

registry.category("services").add("sign_print_report", signPrintReport);