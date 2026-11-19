/** @odoo-module **/

import { NameAndSignature } from "@web/core/signature/name_and_signature";
import { patch } from "@web/core/utils/patch";

patch(NameAndSignature.prototype, {
    setup() {
        super.setup();
    },

    onSelectFont(index) {
        this.currentFont = this.fonts[index];
        const font = this.fonts[index];
        const text = this.getCleanedName();
        const canvas = this.signatureRef.el;
        const img = this.getSVGText(font, text, canvas.width, canvas.height);
        this.printImage(img);
    },
})