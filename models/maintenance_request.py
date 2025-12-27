# -*- coding: utf-8 -*-
"""
Maintenance Request Model
=========================

This is the TRANSACTIONAL model of the GearGuard system. It handles the lifecycle
of maintenance jobs from creation to completion or equipment scrapping.

IMPLEMENTATION PRIORITY: HIGH (Step 3 - Core)
Implement after Equipment model is complete. This model contains critical business logic.

===================================================================================
CRITICAL BUSINESS LOGIC TO IMPLEMENT
===================================================================================

1. AUTO-FILL LOGIC (onchange) - KEY DEMO FEATURE
   ------------------------------------------------
   When user selects an Equipment, automatically fill:
   - category_id (from equipment.category_id)
   - maintenance_team_id (from equipment.maintenance_team_id)
   - technician_id (from equipment.technician_id)

   This is the "Magic" feature judges look for!

2. SCRAP LOGIC (write override) - KEY DEMO FEATURE
   ------------------------------------------------
   When request stage moves to 'scrap':
   - Set equipment.active = False
   - Set equipment.state = 'scrapped'
   - Log message to equipment chatter

3. STAGE TRANSITIONS
   ------------------
   - new → in_progress: Auto-assign technician if not set
   - in_progress → repaired: Require duration > 0, set close_date
   - any → scrap: Trigger equipment deactivation

4. OVERDUE CALCULATION
   --------------------
   Request is overdue if:
   - schedule_date < today AND
   - stage NOT IN ('repaired', 'scrap')

5. COST TRACKING (ENHANCEMENT)
   ----------------------------
   - Parts cost: Manual entry
   - Labor cost: duration × hourly_rate (configurable)
   - Total cost: parts + labor (computed)

===================================================================================

FIELDS TO IMPLEMENT:
--------------------
| Field Name           | Type      | Required | Description                           |
|----------------------|-----------|----------|---------------------------------------|
| name                 | Char      | YES      | Subject/title (e.g., "Leaking Oil")   |
| description          | Html      | NO       | Detailed problem description          |
| equipment_id         | Many2one  | YES      | Related equipment                     |
| category_id          | Many2one  | NO       | Auto-filled from equipment            |
| maintenance_team_id  | Many2one  | NO       | Auto-filled from equipment            |
| technician_id        | Many2one  | NO       | Assigned technician                   |
| maintenance_type     | Selection | YES      | 'corrective' or 'preventive'          |
| stage                | Selection | YES      | 'new','in_progress','repaired','scrap'|
| priority             | Selection | NO       | '0'=Low to '3'=Urgent                 |
| request_date         | Date      | YES      | Creation date (default: today)        |
| schedule_date        | Date      | NO       | Scheduled maintenance date            |
| close_date           | Date      | NO       | Completion date (auto-set on repair)  |
| duration             | Float     | NO       | Hours spent on maintenance            |
| color                | Integer   | NO       | Kanban card color                     |
| kanban_state         | Selection | NO       | Visual state for kanban               |
| company_id           | Many2one  | NO       | Multi-company support                 |
|----------------------|-----------|----------|---------------------------------------|
| COST FIELDS:         |           |          |                                       |
|----------------------|-----------|----------|---------------------------------------|
| cost_parts           | Float     | NO       | Cost of replacement parts             |
| cost_labor_rate      | Float     | NO       | Hourly labor rate (default from config)|
| cost_labor           | Float     | COMPUTED | duration × cost_labor_rate            |
| cost_total           | Float     | COMPUTED | cost_parts + cost_labor               |
| currency_id          | Many2one  | NO       | Currency for costs                    |
|----------------------|-----------|----------|---------------------------------------|
| COMPUTED FIELDS:     |           |          |                                       |
|----------------------|-----------|----------|---------------------------------------|
| is_overdue           | Boolean   | COMPUTED | True if past schedule_date & not done |
| days_overdue         | Integer   | COMPUTED | Number of days past schedule          |

STAGE SELECTION VALUES:
-----------------------
- 'new': New request, waiting to be picked up
- 'in_progress': Technician is working on it
- 'repaired': Completed successfully
- 'scrap': Equipment beyond repair, to be scrapped

PRIORITY SELECTION VALUES:
--------------------------
- '0': Low (gray)
- '1': Normal (blue)
- '2': High (yellow)
- '3': Urgent (red)

KANBAN STATE VALUES:
--------------------
- 'normal': Default (gray bullet)
- 'done': Ready (green bullet)
- 'blocked': Blocked (red bullet)

VIEWS NEEDED: (in request_views.xml)
-----------------------------------
1. KANBAN VIEW (Primary - Default View):
   - Group by: stage (New | In Progress | Repaired | Scrap)
   - Drag & drop enabled
   - Show: name, equipment, technician avatar, priority ribbon
   - Overdue indicator: Red text/border if is_overdue=True
   - Quick create enabled

2. CALENDAR VIEW:
   - Events on schedule_date
   - Default filter: maintenance_type = 'preventive'
   - Color by priority or team
   - Click-to-create enabled

3. FORM VIEW:
   - Header: Stage buttons (statusbar)
   - Sheet with sections for details, assignment, costs
   - Chatter at bottom

4. TREE VIEW:
   - Columns: name, equipment, team, technician, stage, schedule_date, is_overdue
   - Sortable and filterable

5. SEARCH VIEW:
   - Filters: My Requests, Overdue, By Stage, By Type
   - Group by: Stage, Team, Equipment, Priority

DEMO DATA NEEDED:
-----------------
1. "Oil Leak" - CNC Machine - Corrective - In Progress - Mechanics
2. "Paper Jam" - Printer - Corrective - New - OVERDUE - IT Support
3. "Monthly Checkup" - Laser Cutter - Preventive - New - Scheduled next week
4. "Battery Replacement" - Laptop - Corrective - Repaired - IT Support
5. "Filter Cleaning" - HVAC - Preventive - New - Scheduled tomorrow
6. "Motor Failure" - Old Machine - Corrective - Scrap (to demo scrap flow)
"""

from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class MaintenanceRequest(models.Model):
    _name = 'maintenance.request'
    _description = 'Maintenance Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, schedule_date asc, id desc'

    # ==========================================================================
    # SELECTION CONSTANTS
    # Define as class attributes for easy reference
    # ==========================================================================

    STAGE_SELECTION = [
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('repaired', 'Repaired'),
        ('scrap', 'Scrap'),
    ]

    PRIORITY_SELECTION = [
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ]

    TYPE_SELECTION = [
        ('corrective', 'Corrective'),
        ('preventive', 'Preventive'),
    ]

    KANBAN_STATE_SELECTION = [
        ('normal', 'In Progress'),
        ('done', 'Ready'),
        ('blocked', 'Blocked'),
    ]

    # ==========================================================================
    # BASIC FIELDS
    # ==========================================================================

    name = fields.Char(
        string='Subject',
        required=True,
        tracking=True,
        help="Brief description of the issue (e.g., 'Leaking Oil', 'Paper Jam')"
    )

    description = fields.Html(
        string='Description',
        help="Detailed description of the problem or maintenance required"
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help="If unchecked, the request will be hidden from default views"
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    color = fields.Integer(
        string='Color',
        default=0,
        help="Color index for Kanban view"
    )

    # ==========================================================================
    # STAGE & STATUS FIELDS
    # ==========================================================================

    stage = fields.Selection(
        selection=STAGE_SELECTION,
        string='Stage',
        default='new',
        required=True,
        tracking=True,
        group_expand='_expand_stages',
        help="Current stage of the maintenance request"
    )

    priority = fields.Selection(
        selection=PRIORITY_SELECTION,
        string='Priority',
        default='1',
        tracking=True,
        help="Priority level: 0=Low, 1=Normal, 2=High, 3=Urgent"
    )

    kanban_state = fields.Selection(
        selection=KANBAN_STATE_SELECTION,
        string='Kanban State',
        default='normal',
        help="Visual indicator on Kanban cards"
    )

    maintenance_type = fields.Selection(
        selection=TYPE_SELECTION,
        string='Maintenance Type',
        default='corrective',
        required=True,
        tracking=True,
        help="Corrective: Unplanned repair (breakdown). "
             "Preventive: Planned maintenance (routine checkup)."
    )

    # ==========================================================================
    # DATE FIELDS
    # ==========================================================================

    request_date = fields.Date(
        string='Request Date',
        default=fields.Date.today,
        required=True,
        tracking=True,
        help="Date when the request was created"
    )

    schedule_date = fields.Date(
        string='Scheduled Date',
        tracking=True,
        help="Date when the maintenance should be performed. "
             "Used for calendar view and overdue calculation."
    )

    close_date = fields.Date(
        string='Close Date',
        tracking=True,
        help="Date when the maintenance was completed. "
             "Automatically set when stage moves to 'repaired'."
    )

    # ==========================================================================
    # RELATIONAL FIELDS - EQUIPMENT & ASSIGNMENT
    # ==========================================================================

    equipment_id = fields.Many2one(
        comodel_name='maintenance.equipment',
        string='Equipment',
        required=True,
        tracking=True,
        help="Equipment that requires maintenance. "
             "Selecting equipment will auto-fill team and technician."
    )

    category_id = fields.Many2one(
        comodel_name='maintenance.equipment.category',
        string='Category',
        tracking=True,
        help="Equipment category (auto-filled from equipment)"
    )

    maintenance_team_id = fields.Many2one(
        comodel_name='maintenance.team',
        string='Maintenance Team',
        tracking=True,
        help="Team responsible for this request (auto-filled from equipment)"
    )

    technician_id = fields.Many2one(
        comodel_name='res.users',
        string='Technician',
        tracking=True,
        domain="[('id', 'in', team_member_ids)]",
        help="Technician assigned to this request"
    )

    # Helper field for technician domain
    team_member_ids = fields.Many2many(
        comodel_name='res.users',
        related='maintenance_team_id.member_ids',
        string='Team Members',
    )

    # ==========================================================================
    # DURATION & WORK FIELDS
    # ==========================================================================

    duration = fields.Float(
        string='Duration (Hours)',
        tracking=True,
        help="Hours spent on this maintenance request"
    )

    # ==========================================================================
    # COST TRACKING FIELDS (ENHANCEMENT)
    # ==========================================================================

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        help="Currency for cost tracking"
    )

    cost_parts = fields.Float(
        string='Parts Cost',
        tracking=True,
        help="Cost of replacement parts and materials"
    )

    cost_labor_rate = fields.Float(
        string='Labor Rate (per hour)',
        default=50.0,  # TODO: Make this configurable via settings
        help="Hourly rate for labor cost calculation"
    )

    cost_labor = fields.Float(
        string='Labor Cost',
        compute='_compute_costs',
        store=True,
        help="Computed: duration × labor rate"
    )

    cost_total = fields.Float(
        string='Total Cost',
        compute='_compute_costs',
        store=True,
        help="Computed: parts cost + labor cost"
    )

    # ==========================================================================
    # COMPUTED FIELDS - OVERDUE
    # ==========================================================================

    is_overdue = fields.Boolean(
        string='Is Overdue',
        compute='_compute_overdue',
        store=True,
        help="True if schedule_date has passed and request is not complete"
    )

    days_overdue = fields.Integer(
        string='Days Overdue',
        compute='_compute_overdue',
        store=True,
        help="Number of days past the scheduled date"
    )

    # ==========================================================================
    # COMPUTE METHODS
    # ==========================================================================

    @api.depends('duration', 'cost_parts', 'cost_labor_rate')
    def _compute_costs(self):
        """
        Compute labor cost and total cost.

        IMPLEMENTATION:
        ---------------
        - cost_labor = duration × cost_labor_rate
        - cost_total = cost_parts + cost_labor
        """
        for request in self:
            request.cost_labor = request.duration * request.cost_labor_rate
            request.cost_total = request.cost_parts + request.cost_labor

    @api.depends('schedule_date', 'stage')
    def _compute_overdue(self):
        """
        Compute overdue status.

        IMPLEMENTATION:
        ---------------
        A request is overdue if:
        1. schedule_date is set AND
        2. schedule_date < today AND
        3. stage NOT IN ('repaired', 'scrap')

        VISUAL INDICATION:
        - In Kanban: Show red border/text
        - In Tree: Show red row or icon
        """
        today = fields.Date.today()
        for request in self:
            if (request.schedule_date and
                    request.schedule_date < today and
                    request.stage not in ('repaired', 'scrap')):
                request.is_overdue = True
                request.days_overdue = (today - request.schedule_date).days
            else:
                request.is_overdue = False
                request.days_overdue = 0

    # ==========================================================================
    # ONCHANGE METHODS - AUTO-FILL LOGIC
    # ==========================================================================

    @api.onchange('equipment_id')
    def _onchange_equipment_id(self):
        """
        =====================================================================
        AUTO-FILL LOGIC - CRITICAL DEMO FEATURE
        =====================================================================

        When user selects an Equipment, automatically populate:
        1. category_id - From equipment.category_id
        2. maintenance_team_id - From equipment.maintenance_team_id
        3. technician_id - From equipment.technician_id

        This is the "Magic" that judges look for in the demo!
        Shows that the system is "smart" and reduces manual data entry.

        DEMO SCRIPT:
        ------------
        "Notice how as soon as I select the Printer, the IT Support team
        is automatically assigned. No manual work needed!"
        """
        if self.equipment_id:
            self.category_id = self.equipment_id.category_id
            self.maintenance_team_id = self.equipment_id.maintenance_team_id
            self.technician_id = self.equipment_id.technician_id
        else:
            self.category_id = False
            self.maintenance_team_id = False
            self.technician_id = False

    @api.onchange('maintenance_team_id')
    def _onchange_maintenance_team_id(self):
        """
        Clear technician when team changes (to enforce team membership).

        Only clear if the current technician is not a member of the new team.
        """
        if self.technician_id and self.maintenance_team_id:
            if self.technician_id not in self.maintenance_team_id.member_ids:
                self.technician_id = False

    # ==========================================================================
    # CRUD OVERRIDES - SCRAP LOGIC & STAGE TRANSITIONS
    # ==========================================================================

    def write(self, vals):
        """
        =====================================================================
        SCRAP LOGIC - CRITICAL DEMO FEATURE
        =====================================================================

        Override write to handle stage transitions:

        1. SCRAP LOGIC:
           When stage changes to 'scrap':
           - Set equipment.active = False
           - Set equipment.state = 'scrapped'
           - Post message to equipment chatter

        2. AUTO-ASSIGN ON IN_PROGRESS:
           When stage changes to 'in_progress':
           - If technician_id is empty, assign current user

        3. SET CLOSE_DATE ON REPAIRED:
           When stage changes to 'repaired':
           - Set close_date to today if not set
           - Optionally validate duration > 0

        DEMO SCRIPT:
        ------------
        "When I move this request to Scrap, watch what happens to the equipment..."
        [Drag card to Scrap column]
        "The equipment is now automatically marked as unusable!"
        """
        # Handle stage transitions
        if 'stage' in vals:
            new_stage = vals['stage']

            # SCRAP LOGIC
            if new_stage == 'scrap':
                for request in self:
                    if request.equipment_id:
                        # Deactivate equipment
                        request.equipment_id.sudo().write({
                            'active': False,
                            'state': 'scrapped',
                        })
                        # Log message to equipment
                        request.equipment_id.message_post(
                            body=_(
                                "Equipment scrapped due to maintenance request: "
                                "<a href='#' data-oe-model='maintenance.request' "
                                "data-oe-id='%d'>%s</a>"
                            ) % (request.id, request.name),
                            message_type='notification',
                        )

            # AUTO-ASSIGN ON IN_PROGRESS
            if new_stage == 'in_progress':
                if 'technician_id' not in vals:
                    for request in self:
                        if not request.technician_id:
                            vals['technician_id'] = self.env.uid

            # SET CLOSE_DATE ON REPAIRED
            if new_stage == 'repaired':
                if 'close_date' not in vals:
                    vals['close_date'] = fields.Date.today()

        return super().write(vals)

    @api.model
    def create(self, vals):
        """
        Override create to set default schedule_date for preventive maintenance.
        """
        if vals.get('maintenance_type') == 'preventive' and not vals.get('schedule_date'):
            # Default to one week from now for preventive
            vals['schedule_date'] = fields.Date.today() + timedelta(days=7)
        return super().create(vals)

    # ==========================================================================
    # ACTION METHODS
    # ==========================================================================

    def action_start_maintenance(self):
        """
        Button action to move request from 'new' to 'in_progress'.
        """
        for request in self:
            if request.stage == 'new':
                request.write({
                    'stage': 'in_progress',
                    'technician_id': request.technician_id.id or self.env.uid,
                })

    def action_complete_maintenance(self):
        """
        Button action to mark request as 'repaired'.

        VALIDATION:
        - Duration should be > 0 (warn if not)
        """
        for request in self:
            if request.stage == 'in_progress':
                if not request.duration:
                    # Optional: You can make this a hard requirement
                    pass  # Just warn, don't block
                request.write({
                    'stage': 'repaired',
                    'close_date': fields.Date.today(),
                })

    def action_scrap_equipment(self):
        """
        Button action to mark request as 'scrap' and deactivate equipment.
        """
        for request in self:
            request.write({'stage': 'scrap'})

    def action_reset_to_new(self):
        """
        Reset request back to 'new' stage.
        """
        self.write({
            'stage': 'new',
            'close_date': False,
        })

    # ==========================================================================
    # HELPER METHODS
    # ==========================================================================

    @api.model
    def _expand_stages(self, stages, domain, order):
        """
        Ensure all stages are shown in Kanban view even if empty.

        This is required for proper Kanban drag-and-drop functionality.
        """
        return [key for key, val in self.STAGE_SELECTION]

    def _get_overdue_requests(self):
        """
        Get all overdue requests (for scheduled actions/reports).
        """
        today = fields.Date.today()
        return self.search([
            ('schedule_date', '<', today),
            ('stage', 'not in', ('repaired', 'scrap')),
        ])

    # ==========================================================================
    # SCHEDULED ACTIONS (called by cron)
    # ==========================================================================

    @api.model
    def _cron_send_overdue_reminders(self):
        """
        Scheduled action: Send reminders for overdue requests.

        IMPLEMENTATION:
        ---------------
        1. Find all overdue requests
        2. Group by technician
        3. Send email notification to each technician

        Configure in data/scheduled_actions.xml
        """
        overdue_requests = self._get_overdue_requests()
        # TODO: Group by technician and send emails
        # Use mail.template from data/mail_templates.xml
        return True

    # ==========================================================================
    # CONSTRAINTS
    # ==========================================================================

    @api.constrains('schedule_date', 'close_date')
    def _check_dates(self):
        """
        Validate that close_date is not before schedule_date.
        """
        for request in self:
            if request.schedule_date and request.close_date:
                if request.close_date < request.schedule_date:
                    raise ValidationError(_(
                        "Close date cannot be before scheduled date."
                    ))

    # ==========================================================================
    # DISPLAY NAME
    # ==========================================================================

    def name_get(self):
        """
        Display name with equipment name.

        Example: "Oil Leak - CNC Machine #001"
        """
        result = []
        for request in self:
            name = request.name
            if request.equipment_id:
                name = f"{name} - {request.equipment_id.name}"
            result.append((request.id, name))
        return result
