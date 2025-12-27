# -*- coding: utf-8 -*-
"""
Warranty Alert Wizard
=====================

This wizard allows managers to manually send warranty expiration alerts
for selected equipment.

IMPLEMENTATION PRIORITY: LOW (Enhancement)
Implement after core functionality is working.

PURPOSE:
--------
- Manual trigger for warranty alerts
- Bulk send alerts for multiple equipment
- Preview alert before sending

USAGE:
------
1. Select equipment from tree view
2. Action > Send Warranty Alert
3. Wizard shows selected equipment
4. Confirm to send alerts

FIELDS:
-------
| Field Name    | Type     | Description                        |
|---------------|----------|------------------------------------|
| equipment_ids | Many2many| Equipment to send alerts for       |
| template_id   | Many2one | Email template to use              |
| preview       | Html     | Preview of the email               |

METHODS:
--------
1. default_get() - Pre-populate with selected equipment
2. _compute_preview() - Generate email preview
3. action_send_alerts() - Send the alerts

VIEWS NEEDED:
- Form view as wizard dialog
- Action to launch from equipment tree
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class WarrantyAlertWizard(models.TransientModel):
    _name = 'maintenance.warranty.alert.wizard'
    _description = 'Warranty Alert Wizard'

    # ==========================================================================
    # FIELDS
    # ==========================================================================

    equipment_ids = fields.Many2many(
        comodel_name='maintenance.equipment',
        string='Equipment',
        required=True,
        help="Equipment to send warranty alerts for"
    )

    template_id = fields.Many2one(
        comodel_name='mail.template',
        string='Email Template',
        domain="[('model_id.model', '=', 'maintenance.equipment')]",
        help="Email template to use for the alert"
    )

    email_preview = fields.Html(
        string='Email Preview',
        compute='_compute_email_preview',
        help="Preview of the email that will be sent"
    )

    # ==========================================================================
    # DEFAULT VALUES
    # ==========================================================================

    @api.model
    def default_get(self, fields_list):
        """
        Pre-populate wizard with selected equipment from context.

        IMPLEMENTATION:
        ---------------
        Get active_ids from context and filter to equipment with
        warranty_alert = True.

        Example:
        ```python
        res = super().default_get(fields_list)
        if 'equipment_ids' in fields_list:
            active_ids = self.env.context.get('active_ids', [])
            equipment = self.env['maintenance.equipment'].browse(active_ids)
            # Filter to only those with warranty alerts
            equipment_with_alert = equipment.filtered(lambda e: e.warranty_alert)
            res['equipment_ids'] = [(6, 0, equipment_with_alert.ids)]
        return res
        ```
        """
        res = super().default_get(fields_list)

        # Get selected equipment from context
        if 'equipment_ids' in fields_list:
            active_ids = self.env.context.get('active_ids', [])
            if active_ids:
                res['equipment_ids'] = [(6, 0, active_ids)]

        # Set default template
        if 'template_id' in fields_list:
            template = self.env.ref('gearguard.mail_template_warranty_alert', raise_if_not_found=False)
            if template:
                res['template_id'] = template.id

        return res

    # ==========================================================================
    # COMPUTE METHODS
    # ==========================================================================

    @api.depends('equipment_ids', 'template_id')
    def _compute_email_preview(self):
        """
        Generate preview of the email that will be sent.

        IMPLEMENTATION:
        ---------------
        Use the first equipment record to render template preview.
        """
        for wizard in self:
            if wizard.equipment_ids and wizard.template_id:
                # Render template for first equipment
                first_equipment = wizard.equipment_ids[0]
                try:
                    wizard.email_preview = wizard.template_id._render_field(
                        'body_html',
                        [first_equipment.id],
                        compute_lang=True
                    )[first_equipment.id]
                except Exception:
                    wizard.email_preview = '<p>Unable to generate preview</p>'
            else:
                wizard.email_preview = '<p>Select equipment and template to see preview</p>'

    # ==========================================================================
    # ACTION METHODS
    # ==========================================================================

    def action_send_alerts(self):
        """
        Send warranty alerts for selected equipment.

        IMPLEMENTATION:
        ---------------
        1. Validate equipment selection
        2. Loop through equipment
        3. Send email using template
        4. Log activity/message

        Example:
        ```python
        self.ensure_one()
        if not self.equipment_ids:
            raise UserError(_("Please select at least one equipment."))

        if not self.template_id:
            raise UserError(_("Please select an email template."))

        for equipment in self.equipment_ids:
            self.template_id.send_mail(equipment.id, force_send=True)
            equipment.message_post(
                body=_("Warranty alert sent."),
                message_type='notification'
            )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Alerts Sent"),
                'message': _("%d warranty alerts have been sent.") % len(self.equipment_ids),
                'type': 'success',
                'sticky': False,
            }
        }
        ```
        """
        self.ensure_one()

        if not self.equipment_ids:
            raise UserError(_("Please select at least one equipment."))

        # TODO: Implement actual email sending
        # For now, just log a message
        for equipment in self.equipment_ids:
            equipment.message_post(
                body=_("Warranty alert notification (wizard triggered)."),
                message_type='notification'
            )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Alerts Sent"),
                'message': _("%d warranty alerts have been processed.") % len(self.equipment_ids),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_cancel(self):
        """Cancel the wizard."""
        return {'type': 'ir.actions.act_window_close'}
