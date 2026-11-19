/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { rpc } from "@web/core/network/rpc";
import { renderToString } from "@web/core/utils/render";
import { Component, onWillStart, onMounted, useEffect, useRef } from "@odoo/owl";
import { uniqueId } from "@web/core/utils/functions";
import { setRecurringAnimationFrame, debounce } from "@web/core/utils/timing";
import { SignatureDialog } from "@web/core/signature/signature_dialog";
import { LinkDialog } from "./linkdialog";
import { WarningDialog } from "@web/core/errors/error_dialogs";

class SignPrintReportAction extends Component {
    setup() { 
        this.iframeRef = useRef("iframe");
        this.errorRef = useRef("error");

        this.sign_print_report = useService("sign_print_report");
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.notification = useService("notification");

        this.iframePageTracker = {};
        this.partner = false;

        this.isDragging = false;
        
        if(this.sign_print_report.params){
            const metaData = Object.assign({}, this.sign_print_report.params, {
                active_id : this.sign_print_report.params.active_id || false,
                active_model : this.sign_print_report.params.active_model || false,
                report_name : this.sign_print_report.params.report_name || false,
                data : this.sign_print_report.params.data || false,
                name : this.sign_print_report.params.name || 'report.pdf',
            });
            this.data = metaData;
        }
        else{
            return;
        }
        this.orm = useService("orm");
        onWillStart(this.onWillStart);
        onMounted(this.onMounted);
    }

    async onWillStart(){
        const partner = await this.orm.call("res.partner", "search_read", [], {
            fields: ['id', 'name', 'phone', 'website', 'email', 'company_name', 'report_signature'],
            domain: [['id', '=', parseInt(user.partnerId)]],
            limit: 1,
        });
        if (partner){
            this.partner = partner[0];
        }
    }

    onMounted() {
        var self = this;
        if (this.data.data) {
            this.url = URL.createObjectURL(this.data.data);
        } else {
            return;
        }
        
        this.pdfjs = '/web/static/lib/pdfjs/web/viewer.html?';
        this.report_data = "file=" + this.url + "#page=1&zoom=100";
        this.location = this.pdfjs + this.report_data;
    
        this.$iframe = this.iframeRef.el;
        
        this.$iframe.addEventListener("load", function () {
            self.waitForLoadPDF();
        }, { once: true });

        this.$iframe.setAttribute('src', this.location);
        this.$error = this.errorRef.el;
        if (this.$error.parentNode) {
            this.$error.parentNode.removeChild(this.$error);
        }
    }       

    async waitForLoadPDF() {
        var self = this;
        if (!this.$iframe.contentWindow || !this.$iframe.contentWindow.document ||  !this.$iframe.contentWindow.document.documentElement) {
            return this.dialogService.add(WarningDialog, {
                title: _t("Warning"),
                message: _t("To add signature fields, you'll need a valid PDF!"),
            });
        }

        const iframeDocument = this.$iframe.contentWindow.document;
        const iframePageCount = iframeDocument.querySelectorAll('.page').length;
        const iframeLayerCount = iframeDocument.querySelectorAll('.textLayer').length;
    
        if (iframePageCount > 0 && iframeLayerCount > 0) {
            this.iframePageCount = iframePageCount;
            await this.afterLoadPDF();
        } else {
            setTimeout(function () {
                self.waitForLoadPDF();
            }, 10);
        }
    }    

    async afterLoadPDF() {
        var self = this;

        const iframeDocument = this.$iframe.contentWindow.document;
        const html = iframeDocument.documentElement;

        if (self.env.isSmall) {
            html.querySelector('button#zoomIn').click();
        } else {
            html.querySelector('button#zoomOut').click();
            html.querySelector('button#zoomOut').click();
        }
        
        const elementsToHide = html.querySelectorAll(
            '#pageRotateCw, #pageRotateCcw, #openFile, #viewBookmark, #print, #presentationMode, #download'
        );
        elementsToHide.forEach(element => element.style.display = 'none');
        
        const lastPageNext = html.querySelector('#lastPage')?.nextElementSibling;
        if (lastPageNext) lastPageNext.style.display = 'none';
        
        for (let i = 1; i <= this.iframePageCount; i++) {
            this.iframePageTracker[i] = [];
        }
        
        const assets = await rpc("/sign_print_report/render_assets_pdf_iframe", {
            args: [{ debug: this.env.debug }]
        });

        html.querySelector("head").insertAdjacentHTML("beforeend", assets);

        self.buildDragAndDropSnippet();

        function iframeRefreshInterval() {
            try {
                self.signBlockItemsRefresh();
                self.iframe_refresh_timer = setTimeout(iframeRefreshInterval, 1000);
            } catch (e) {
                
            }
        }
        iframeRefreshInterval();
    }

    buildDragAndDropSnippet() {
        const self = this;
        const iframeDocument = this.$iframe.contentDocument;
        const html = iframeDocument.querySelector('html');
    
        const snippetButtons = renderToString("sign_print_report.drag_and_drop_buttons");
        self.$snippetButtonsToolbarttons = document.createElement('div');
        self.$snippetButtonsToolbarttons.classList.add('o_sign_drop_type_toolbar', 'd-flex', 'flex-column');
        html.querySelector('body').prepend(self.$snippetButtonsToolbarttons);
    
        html.querySelector('#outerContainer').classList.add('o_sign_drop_type_toolbar_visible');
        self.$snippetButtonsToolbarttons.innerHTML = snippetButtons;
    
        html.querySelectorAll(".o_sign_drop_type_button").forEach((sidebarItem) => {
            sidebarItem.setAttribute("draggable", true);
            sidebarItem.addEventListener("dragstart", (e) => this.onSidebarDragStart(e));
            sidebarItem.addEventListener("dragend", (e) => this.onSidebarDragEnd(e));
        });
    
        html.querySelectorAll(".page").forEach((page) => {
            page.addEventListener("dragover", (e) => this.onDragOver(e));
            page.addEventListener("drop", (e) => this.onDrop(e));
            page.addEventListener("mouseup", (e) => this.onPageMouseUp(e));
        });
    }    

    offsetPosition(el) {
        const box = el.getBoundingClientRect();
        const docElem = document.documentElement;
        return {
            top: box.top + window.scrollY - docElem.clientTop,
            left: box.left + window.scrollY - docElem.clientLeft,
        };
    }
    
    onSidebarDragEnd(e) {
        const iframeDocument = this.$iframe.contentWindow.document;
        const html = iframeDocument.documentElement;
        const firstPage = html.querySelector('.page[data-page-number="1"]');
        firstPage.removeChild(this.phantomSignItem);
    }

    onSidebarDragStart(e) {
        const iframeDocument = this.$iframe.contentDocument;
        const html = iframeDocument.querySelector('html');
        
        const tmpSignItem = this.createSignBlockItem(e.target.dataset.type);
        const firstPage = html.querySelector('.page[data-page-number="1"]');
        firstPage.insertAdjacentHTML("beforeend", tmpSignItem);
        this.phantomSignItem = firstPage.lastElementChild;
        this.phantomSignItem.style.cursor = "grab";
        this.phantomSignItem.style.width = "31.9%";
        this.phantomSignItem.style.height = "3.9%";
    
        e.dataTransfer.setDragImage(this.phantomSignItem, 0, 0);
        e.dataTransfer.setData("type", e.target.dataset.type);
        e.dataTransfer.setData("width", 0.319);
        e.dataTransfer.setData("height", 0.039);
    
        this.cleanDnD = this.startSmoothDragDrop(
            html.querySelector("#viewerContainer"),
            e.currentTarget,
            this.phantomSignItem,
        );
    
        requestAnimationFrame(() => {
            if (this.phantomSignItem) {
                this.phantomSignItem.style.visibility = "hidden";
            }
        });
    }    

    onDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
    }

    onDrop(e) {
        e.preventDefault();
        const self = this;
        const page = e.currentTarget;
        const textLayer = page.querySelector(".textLayer");
        const containerOffset = self.offsetPosition(textLayer);
        const targetPage = Number(page.dataset.pageNumber);
        const type = e.dataTransfer.getData("type");
        
        const width = e.dataTransfer.getData("width");
        const height = e.dataTransfer.getData("height");
    
        const posX = (e.clientX - containerOffset.left) / textLayer.clientWidth;
        const posY = (e.clientY - containerOffset.top) / textLayer.clientHeight;
        
        const tmpSignItem = self.createSignBlockItem(type);
        const tmpContainer = document.createElement('div');
        tmpContainer.innerHTML = tmpSignItem;
        const tmpNewElement = tmpContainer.firstElementChild;
        const newSignBlockItem = tmpNewElement.cloneNode(true);
    
        const vals = {
            posX: posX,
            posY: posY,
            page: targetPage,
            type: type,
            width: width,
            height: height,
        };
    
        Object.keys(vals).forEach(key => {
            newSignBlockItem.dataset[key] = vals[key];
        });
    
        self.appendSignBlockItemonPage(newSignBlockItem);
        self.updateSignBlockItem(newSignBlockItem);
    }    
    onPageMouseUp(e){
        if(!e.target.closest('.sign_block_item')) {
            return;
        }
        
        const signItem = e.currentTarget;    
        this.startSmoothDragResize(e, signItem);
    }
    signBlockItemsRefresh() {
        const self = this;
        const iframeDocument = this.$iframe.contentDocument || this.$iframe.contentWindow.document;
        const html = iframeDocument.documentElement;
        for (const page in this.iframePageTracker) {
            const iframePageContainer = html.querySelector('.page[data-page-number="' + page + '"]');
            for (const id in this.iframePageTracker[page]) {
                const item = this.iframePageTracker[page][id];
                if (!item.parentElement || !item.parentElement.classList.contains("page")) {
                    iframePageContainer.append(item);
                }
            }

        }
        self.updateFontSizeByItem();
    }    
    createSignBlockItem(type) {
        var self = this;
        var type = type ? type : 'name';
        var partnerInfo = self.partner;

        var name = partnerInfo.name;
        var email = partnerInfo.email;
        var company_name = partnerInfo.company_name;
        var phone = partnerInfo.phone;
        var website = partnerInfo.website;
        var report_signature = partnerInfo.report_signature ? 'data:image/png;base64,' + partnerInfo.report_signature : false;
        var date = new Date().toISOString().replace(/T|Z/g, ' ').trim().substring(0, 19);

        var vals = {
            'name' :  name,
            'email' :  email,
            'phone' :  phone,
            'website' :  website,
            'company' :  company_name,
            'date':  date,
            'signature' : report_signature,
        }
        var $signDropBlocks = renderToString("sign_print_report.drag_and_drop_blocks", {
            type : type,
            data : vals,
        });
        return $signDropBlocks
    }

    appendSignBlockItemonPage($signBlockItem) {
        var self = this;

        const iframeDocument = this.$iframe.contentWindow.document;
        const html = iframeDocument.documentElement;

        var page = $signBlockItem.dataset.page;
        var type = $signBlockItem.dataset.type;

        const $page = html.querySelector('.page[data-page-number="' + page + '"]');
        if (!$signBlockItem.parentElement || !$signBlockItem.parentElement.classList.contains("page")) {
            $page.appendChild($signBlockItem);
            var unique_id = uniqueId();
            $signBlockItem.setAttribute('unique_id', parseInt(unique_id));
            self.iframePageTracker[parseInt(page)].push($signBlockItem);
        }
    
        if (type === 'signature') {
            $signBlockItem.style.cursor = 'pointer';
            $signBlockItem.ondblclick = function (ev) {
                ev.preventDefault();
                let defaultName = "";
                const nameAndSignatureProps = {
                    mode: "auto",
                    displaySignatureRatio: 3,
                    signatureType: "signature",
                    noInputName: true,
                };
    
                if (user.name) {
                    defaultName = user.name;
                }
                nameAndSignatureProps.defaultFont = '';
    
                const dialogProps = {
                    defaultName,
                    nameAndSignatureProps,
                    uploadSignature: (signature) => self.uploadSignature(signature),
                };
                self.dialogService.add(SignatureDialog, dialogProps);
            };
        }
    
        var trashIcon = $signBlockItem.querySelector('.fa-trash');
        if (trashIcon) {
            trashIcon.onclick = function (ev) {
                ev.preventDefault();
                self.deleteSignBlockItem(ev.target.parentElement);
            };
        }
    }    

    uploadSignature({ signatureImage }) {
        var self = this;

        const base64String = signatureImage.split('data:image/png;base64,')[1];

        self.orm.write('res.partner', [user.partnerId], {
            ['report_signature']: base64String,
        });

        for (var page in this.iframePageTracker) {
            for (var i = 0; i < this.iframePageTracker[page].length; i++) {                    
                if (this.iframePageTracker[page][i].dataset.type === 'signature'){
                    if (base64String){
                        var img = this.iframePageTracker[page][i].querySelector('.sign_text img');
                        if(img){
                            img.setAttribute('src', 'data:image/png;base64,' + base64String);
                        }else{
                            var sign_text = this.iframePageTracker[page][i].querySelector('.sign_text');
                            var img = "<img src='data:image/png;base64," + base64String + "' style='width: 100%; height: 100%' alt='Signature'/>";
                            sign_text.innerHTML = img;

                        }
                    }
                }
            }
        } 
    }
    updateSignBlockItem($signBlockItem) {
        var self = this;

        var posX = $signBlockItem.dataset.posX , posY = $signBlockItem.dataset.posY;
        var width = $signBlockItem.dataset.width, height = $signBlockItem.dataset.height;
        
        if (posX === undefined ||  posY === undefined ){
            return;
        }

        if (posX < 0) {posX = 0;}
        else if (posX + width > 1.0) {posX = 1.0 - width;}

        if (posY < 0) {posY = 0;}
        else if (posY + height > 1.0) {posY = 1.0 - height;}

        $signBlockItem.dataset.posX = (Math.round(posX * 1000) / 1000).toString();
        $signBlockItem.dataset.posY = (Math.round(posY * 1000) / 1000).toString();

        var width = width * 100 + '%';
        var height = height * 100 + '%';
        var posX = posX * 100 + '%';
        var posY = posY * 100 + '%';
        var textAlign = 'center';

        $signBlockItem.style.width = width;
        $signBlockItem.style.height = height;
        $signBlockItem.style.left = posX;
        $signBlockItem.style.top = posY;
        $signBlockItem.style.textAlign = textAlign;
        $signBlockItem.style.resize = 'both';
        self.enableDroppableOptions($signBlockItem);
    }
    enableDroppableOptions(signBlockItem) {
        const handle = signBlockItem.querySelector(".fa-arrows");
        handle.setAttribute("draggable", true);
        handle.addEventListener("dragstart", (e) => this.onDragStart(e));
        handle.addEventListener("dragend", (e) => this.onDragEnd(e));

        signBlockItem.addEventListener("mouseup", (e) => this.onMouseUp(e));
        signBlockItem.addEventListener("mousedown", (e) => this.onMouseDown(e));
        signBlockItem.addEventListener("mousemove", (e) => this.onMouseMove(e));
    }
    onDragStart(e) {
        const signItem = e.currentTarget.parentElement;
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setDragImage(signItem, 0, 0);
        e.dataTransfer.setData("type", signItem.dataset.type);
        e.dataTransfer.setData("width", signItem.dataset.width);
        e.dataTransfer.setData("height", signItem.dataset.height);
    
        requestAnimationFrame(() => {
            if (signItem) {
                signItem.style.visibility = "hidden";
                this.deleteSignBlockItem(signItem);
            }
        });
    
        const iframeDocument = this.$iframe.contentDocument || this.$iframe.contentWindow.document;
        const html = iframeDocument.documentElement;
    
        this.cleanDnD = this.startSmoothDragDrop(
            html.querySelector("#viewerContainer"),
            signItem,
            null
        );
    }    

    onDragEnd(e) {
        this.cleanDnD();
    }

    onMouseUp(e) {
        const signItem = e.target;
        const page = signItem.parentElement;
        const textLayer = page.querySelector(".textLayer");
        if (!textLayer){
            return;
        }

        var width = Math.round((signItem.offsetWidth / textLayer.clientWidth) * 1000) / 1000;
        var height = Math.round((signItem.offsetHeight / textLayer.clientHeight * 1000)) / 1000;
    
        signItem.style.width = width * 100 + '%';
        signItem.style.height = height * 100 + '%';
    
        signItem.dataset.width = width;
        signItem.dataset.height = height;
    
        this.startSmoothDragResize(e, signItem);
    }    
    
    onMouseDown(e){
        if(!e.target.closest('.sign_block_item')) {
            return;
        }
    }

    onMouseMove(e){
        if(!e.target.closest('.sign_block_item')) {
            return;
        }
        const signItem = e.currentTarget;
        this.startSmoothDragResize(e, signItem);
    }
    startSmoothDragResize(e, signItem) {
        const computedStyle = window.getComputedStyle(signItem);
        const signItemComputedWidth = parseInt(computedStyle.width);
        const signItemComputedHeight = parseInt(computedStyle.height);
    
        const dX = e.clientX - e.x;
        const dY = e.clientY - e.y;
    
        let factX = (dX + signItemComputedWidth) / signItemComputedWidth;
        let factY = (dY + signItemComputedHeight) / signItemComputedHeight;
    
        if (dX < 0 && Math.abs(dX) >= signItemComputedWidth) {
            factX = 1;
        }
    
        if (dY < 0 && Math.abs(dY) >= signItemComputedHeight) {
            factY = 1;
        }

        const width = this.normalizeDimension(factX * parseFloat(signItem.dataset.width), parseFloat(signItem.dataset.posX));
        const height = this.normalizeDimension(factY * parseFloat(signItem.dataset.height), parseFloat(signItem.dataset.posY));
    
        signItem.style.width = width * 100 + '%';
        signItem.style.height = height * 100 + '%';
    }    
    normalizeDimension(dimension, position) {
        if (position + dimension > 1) {
            return 1 - position;
        }
        return dimension;
    }
    startSmoothDragDrop(container, element, dragElement = null, helper){
        const border = 0.2;
        const positions = {
            left: -1,
            right: 1,
            up: -1,
            down: 1,
        };
        const event = {};
        const offsetPosition = this.offsetPosition(container);
        const dragAmount = 10;
        const el = dragElement || element;
        function updateEventPosition(e) {
            event.x = e.clientX - offsetPosition.left;
            event.y = e.clientY - offsetPosition.top;
        }
        const debouncedOnMouseMove = debounce(updateEventPosition, "animationFrame", true);
        container.addEventListener("dragover", debouncedOnMouseMove);
        const sanitize = setRecurringAnimationFrame(() => {
            const { x, y } = event;
            let scrollX,
                scrollY = 0;
            if (x <= container.clientWidth * border) {
                scrollX = positions.left * dragAmount;
            } else if (x >= container.clientWidth * (1 - border)) {
                scrollX = positions.right * dragAmount;
            }

            if (y <= container.clientHeight * border) {
                scrollY = positions.up * dragAmount;
            } else if (y >= container.clientHeight * (1 - border)) {
                scrollY = positions.down * dragAmount;
            }
            container.scrollBy(scrollX, scrollY);
        });
        return () => {
            sanitize();
            container.removeEventListener("dragover", debouncedOnMouseMove);
        };
    }

    updateFontSizeByItem() {
        var self = this;
        const iframeDocument = this.$iframe.contentWindow.document;
        const html = iframeDocument.documentElement;
    
        const signBlockItems = html.querySelectorAll('.sign_block_item');
        signBlockItems.forEach(function (el) {
            self.updateFontSizeByItems(el);
        });
    }
    

    updateFontSizeByItems($signBlockItem) {
        var self = this;
        if (!$signBlockItem) {
            return;
        }
        var types = ['name', 'email', 'phone', 'website', 'company', 'date'];
        const iframeDocument = this.$iframe.contentWindow.document;
        const iframePage = iframeDocument.querySelector('.page');
        if (iframePage) {
            const size = types.includes($signBlockItem.dataset.type)
                ? iframePage.clientHeight * 0.015
                : parseFloat($signBlockItem.clientHeight) * 0.4;
            const signTextElements = $signBlockItem.querySelectorAll('.sign_text');
            for (let i = 0; i < signTextElements.length; i++) {
                signTextElements[i].style.fontSize = size + 'px';
            }
        }
    }    

    deleteSignBlockItem($signBlockItem) {
        var self = this;  
        const page = parseInt($signBlockItem.parentElement.getAttribute('data-page-number'));
        Object.keys(self.iframePageTracker[page]).forEach(function (item) {
            var trackerItemId = self.iframePageTracker[page][item] && self.iframePageTracker[page][item].getAttribute('unique_id');
            var blockItemId = $signBlockItem.getAttribute('unique_id');
            if (trackerItemId === blockItemId) {
                var splice = self.iframePageTracker[page].splice(item, 1);
                if (splice) {
                    $signBlockItem.remove();
                }
            }
        });
    }

    onClickSign(){
        var report_data = this.data.data;
        debounce(this._onClickSign(report_data), 200);;
    }

    async _onClickSign(report_data){
        var self = this;            
        var report_data = await self.getBase64(report_data);
        report_data = report_data.substring(report_data.indexOf(',') + 1);
        var report_items = []
        var defs = [];
        for (var page in this.iframePageTracker) {
            for (var i = 0; i < this.iframePageTracker[page].length; i++) {                  
                if (this.iframePageTracker[page][i]){
                    var $signBlockItem = this.iframePageTracker[page][i];
                    var vals = {
                        posX: parseFloat(Math.round($signBlockItem.dataset.posX * 1000)/ 1000),
                        posY: parseFloat(Math.round($signBlockItem.dataset.posY * 1000)/ 1000),
                        width: parseFloat($signBlockItem.dataset.width),
                        height: parseFloat($signBlockItem.dataset.height),
                        page: parseInt($signBlockItem.dataset.page),
                        type : $signBlockItem.dataset.type,
                    };
                    report_items.push(vals)
                }
            }
        }
        if (!report_items.length){
            self.notification.add(
                self.env._t(
                    "At least one sign item is required to sign the report."
                ),
                {
                    type: "danger",
                    title: self.env._t("Warning.") 
                }
            );
        }else{
            if (report_data){
                defs.push(await rpc("/sign_print_report/sign_print_report_data/",{
                        active_id: self.data.active_id,
                        active_model: self.data.active_model,
                        report_items: report_items,
                        report_data: report_data.substring(report_data.indexOf(',') + 1),
                    }));

                return Promise.all(defs).then(async function (data) {
                    if(data){                            
                        var data = "data:application/pdf;base64," + data;
                        fetch(data).then(r => r.blob().then( data => {
                            var file = new File( [data], String(self.name) + "_signed.pdf" ,{ type: "application/pdf" });
                            var signedurl = URL.createObjectURL(file);
                            self.openOutputLink(signedurl);
                        }));
                    }
                });
            }
        }
    }

    openOutputLink(signedurl) {
        var self = this;
        if (signedurl) {
            var content = document.createElement('div'); // Create a div element
            var downloadLink = document.createElement('a'); // Create an anchor element
            downloadLink.setAttribute('href', signedurl);
            downloadLink.setAttribute('target', '_blank');
            downloadLink.setAttribute('class', 'underline-on-hover');
            downloadLink.innerText = "Download the Signed Report by clicking here.";
            content.appendChild(downloadLink); // Append the link to the content div
            self.dialogService.add(LinkDialog, {
                downloadLink: downloadLink,
            });
        }
    }    

    getBase64(file) {
        var self = this;
        if (!file) {
            return Promise.reject();
        }
        return new Promise(function (resolve, reject) {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = function () {
                resolve(reader.result);
            }
            reader.onerror = function (error) {
                reject(error)
            }
        });
    }

    async onClickClose() {
        this.sign_print_report.close()
    }
}

SignPrintReportAction.components = {

};
SignPrintReportAction.template = "sign_print_report.SignPrintReportAction";
SignPrintReportAction.target = "fullscreen";

registry.category("lazy_components").add("SignPrintReportAction", SignPrintReportAction);
registry.category("actions").add("widget_sign_print_report", SignPrintReportAction);
