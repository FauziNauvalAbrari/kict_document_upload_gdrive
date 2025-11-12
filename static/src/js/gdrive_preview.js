/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";

class GDrivePreviewController extends FormController {
    async onRecordChanged(record) {
        super.onRecordChanged(record);
        const iframe = this.el.querySelector(".gdrive-preview");
        if (iframe && record.data.drive_file_id) {
            iframe.src = `https://drive.google.com/file/d/${record.data.drive_file_id}/preview`;
        } else if (iframe) {
            iframe.src = "";
        }
    }
}

registry.category("views").add("gdrive_preview_form", {
    ...registry.category("views").get("form"),
    Controller: GDrivePreviewController,
});
