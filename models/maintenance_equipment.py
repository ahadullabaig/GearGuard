# -*- coding: utf-8 -*-
"""
Maintenance Equipment Model
===========================

This is the CENTRAL model of the GearGuard system. It represents company assets
(machines, vehicles, computers, etc.) that require maintenance tracking.

IMPLEMENTATION PRIORITY: HIGH (Step 2 - Core)
Implement after Category and Team models are complete.

BUSINESS LOGIC:
---------------
1. Equipment can be owned by Department OR Employee (owner_type selection)
2. Each equipment has a default Maintenance Team and Technician
3. When equipment is selected in a Request, team/technician auto-fill
4. Equipment can be in states: operational, maintenance, scrapped
5. SCRAP LOGIC: When a request moves to 'scrap' stage, equipment.active = False
6. WARRANTY ALERTS: Computed field shows if warranty expires within 30 days
7. SMART BUTTON: Shows count of related maintenance requests
8. COST TRACKING: Aggregates total maintenance costs from all requests
9. HISTORY: Tracks maintenance statistics (MTBF, total downtime, etc.)

FIELDS TO IMPLEMENT:
--------------------
| Field Name              | Type      | Required | Description                              |
|-------------------------|-----------|----------|------------------------------------------|
| name                    | Char      | YES      | Equipment name                           |
| serial_number           | Char      | NO       | Unique serial/asset number               |
| active                  | Boolean   | NO       | Archive flag (False when scrapped)       |
| image                   | Binary    | NO       | Equipment photo                          |
| category_id             | Many2one  | NO       | Equipment category                       |
| owner_type              | Selection | NO       | 'department' or 'employee'               |
| department_id           | Many2one  | NO       | Owning department (if owner_type=dept)   |
| employee_id             | Many2one  | NO       | Owning employee (if owner_type=employee) |
| maintenance_team_id     | Many2one  | YES      | Default maintenance team                 |
| technician_id           | Many2one  | NO       | Default technician (from team members)   |
| location                | Char      | NO       | Physical location                        |
| purchase_date           | Date      | NO       | Purchase/acquisition date                |
| warranty_date           | Date      | NO       | Warranty expiration date                 |
| state                   | Selection | NO       | 'operational','maintenance','scrapped'   |
| notes                   | Html      | NO       | Additional notes/documentation           |
| company_id              | Many2one  | NO       | Multi-company support                    |
|-------------------------|-----------|----------|------------------------------------------|
| COMPUTED FIELDS:        |           |          |                                          |
|-------------------------|-----------|----------|------------------------------------------|
| request_count           | Integer   | COMPUTED | Total maintenance requests               |
| open_request_count      | Integer   | COMPUTED | Open (non-closed) requests               |
| warranty_alert          | Boolean   | COMPUTED | True if warranty expires in 30 days      |
| days_to_warranty_end    | Integer   | COMPUTED | Days until warranty expires              |
| total_maintenance_cost  | Float     | COMPUTED | Sum of all request costs                 |
| total_downtime          | Float     | COMPUTED | Sum of all request durations (hours)     |
| last_maintenance_date   | Date      | COMPUTED | Most recent maintenance completion       |
| mtbf                    | Float     | COMPUTED | Mean Time Between Failures (days)        |

METHODS TO IMPLEMENT:
--------------------
1. _compute_request_count() - Count related requests
2. _compute_warranty_alert() - Check warranty expiration
3. _compute_maintenance_stats() - Calculate cost, downtime, MTBF
4. action_view_requests() - Smart button action
5. _onchange_owner_type() - Clear department/employee based on selection
6. _onchange_maintenance_team_id() - Filter technician to team members

SMART BUTTON (Critical Feature):
-------------------------------
On the Equipment form, add a button labeled "Maintenance" that:
- Shows badge with open request count
- When clicked, opens filtered list of requests for this equipment

VIEWS NEEDED: (in equipment_views.xml)
- Form view: Full details with smart button, warranty indicator, history tab
- Tree view: List with key columns, warranty alert indicator
- Kanban view: Cards with image, state badge, warranty alert
- Search view: Filters by category, team, state, warranty alert

WARRANTY ALERT DISPLAY:
- In form view: Show red/yellow banner when warranty expiring
- In kanban: Show warning icon on card
- In tree: Show colored indicator column

DEMO DATA NEEDED:
- CNC Machine #001 (Production, Mechanics, warranty expiring soon)
- Laser Cutter #002 (Production, Mechanics)
- Office Printer #003 (IT Dept, IT Support)
- Company Laptop #004 (Employee: John, IT Support)
- HVAC Unit #005 (Facilities, Electricians)
- Old Machine #006 (to be scrapped in demo)
"""

from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MaintenanceEquipment(models.Model):
    _name = 'maintenance.equipment'
    _description = 'Maintenance Equipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    # ==========================================================================
    # BASIC FIELDS
    # ==========================================================================

    name = fields.Char(
        string='Equipment Name',
        required=True,
        tracking=True,
        help="Name or title of the equipment (e.g., 'CNC Machine #001')"
    )

    serial_number = fields.Char(
        string='Serial Number',
        copy=False,
        tracking=True,
        help="Unique serial number or asset tag for this equipment"
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help="If unchecked, the equipment is considered scrapped/retired. "
             "This is automatically set to False when a request moves to 'Scrap' stage."
    )

    image = fields.Binary(
        string='Image',
        attachment=True,
        help="Photo or image of the equipment"
    )

    state = fields.Selection(
        selection=[
            ('operational', 'Operational'),
            ('maintenance', 'Under Maintenance'),
            ('scrapped', 'Scrapped'),
        ],
        string='Status',
        default='operational',
        tracking=True,
        help="Current operational status of the equipment"
    )

    location = fields.Char(
        string='Location',
        tracking=True,
        help="Physical location of the equipment (e.g., 'Building A, Floor 2')"
    )

    notes = fields.Html(
        string='Notes',
        help="Additional notes, documentation, or specifications"
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
        help="Company this equipment belongs to"
    )

    # ==========================================================================
    # DATE FIELDS
    # ==========================================================================

    purchase_date = fields.Date(
        string='Purchase Date',
        tracking=True,
        help="Date when the equipment was purchased or acquired"
    )

    warranty_date = fields.Date(
        string='Warranty Expiration',
        tracking=True,
        help="Date when the warranty expires. Used for warranty alerts."
    )

    # ==========================================================================
    # OWNERSHIP FIELDS
    # ==========================================================================

    owner_type = fields.Selection(
        selection=[
            ('department', 'Department'),
            ('employee', 'Employee'),
        ],
        string='Owner Type',
        default='department',
        tracking=True,
        help="Specify whether this equipment belongs to a department or an individual employee"
    )

    department_id = fields.Many2one(
        comodel_name='hr.department',
        string='Department',
        tracking=True,
        help="Department that owns this equipment (when Owner Type = Department)"
    )

    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        tracking=True,
        help="Employee assigned to this equipment (when Owner Type = Employee)"
    )

    # ==========================================================================
    # MAINTENANCE ASSIGNMENT FIELDS
    # ==========================================================================

    category_id = fields.Many2one(
        comodel_name='maintenance.equipment.category',
        string='Category',
        tracking=True,
        help="Category of equipment (e.g., Machinery, IT Equipment, Vehicles)"
    )

    maintenance_team_id = fields.Many2one(
        comodel_name='maintenance.team',
        string='Maintenance Team',
        required=True,
        tracking=True,
        help="Default team responsible for maintaining this equipment. "
             "Auto-filled into maintenance requests."
    )

    technician_id = fields.Many2one(
        comodel_name='res.users',
        string='Technician',
        tracking=True,
        domain="[('id', 'in', team_member_ids)]",
        help="Default technician for this equipment. Should be a member of the Maintenance Team."
    )

    # Helper field for technician domain
    team_member_ids = fields.Many2many(
        comodel_name='res.users',
        related='maintenance_team_id.member_ids',
        string='Team Members',
        help="Members of the selected maintenance team (for domain filtering)"
    )

    # ==========================================================================
    # RELATIONAL FIELDS
    # ==========================================================================

    # TODO: Uncomment after maintenance.request is implemented
    # request_ids = fields.One2many(
    #     comodel_name='maintenance.request',
    #     inverse_name='equipment_id',
    #     string='Maintenance Requests',
    #     help="All maintenance requests for this equipment"
    # )

    # ==========================================================================
    # COMPUTED FIELDS - REQUEST COUNTS
    # ==========================================================================

    request_count = fields.Integer(
        string='Maintenance Requests',
        compute='_compute_request_counts',
        store=False,
        help="Total number of maintenance requests for this equipment"
    )

    open_request_count = fields.Integer(
        string='Open Requests',
        compute='_compute_request_counts',
        store=False,
        help="Number of open (not repaired/scrapped) requests"
    )

    # ==========================================================================
    # COMPUTED FIELDS - WARRANTY ALERTS
    # ==========================================================================

    warranty_alert = fields.Boolean(
        string='Warranty Alert',
        compute='_compute_warranty_alert',
        store=True,
        help="True if warranty expires within 30 days"
    )

    days_to_warranty_end = fields.Integer(
        string='Days to Warranty End',
        compute='_compute_warranty_alert',
        store=True,
        help="Number of days until warranty expires (negative if expired)"
    )

    warranty_state = fields.Selection(
        selection=[
            ('valid', 'Valid'),
            ('expiring', 'Expiring Soon'),
            ('expired', 'Expired'),
            ('none', 'No Warranty'),
        ],
        string='Warranty Status',
        compute='_compute_warranty_alert',
        store=True,
        help="Current warranty status for visual indicators"
    )

    # ==========================================================================
    # COMPUTED FIELDS - MAINTENANCE STATISTICS (ENHANCEMENT)
    # ==========================================================================

    total_maintenance_cost = fields.Float(
        string='Total Maintenance Cost',
        compute='_compute_maintenance_stats',
        store=False,
        help="Sum of all maintenance request costs for this equipment"
    )

    total_downtime = fields.Float(
        string='Total Downtime (Hours)',
        compute='_compute_maintenance_stats',
        store=False,
        help="Sum of all maintenance durations (hours)"
    )

    last_maintenance_date = fields.Date(
        string='Last Maintenance',
        compute='_compute_maintenance_stats',
        store=False,
        help="Date of most recent completed maintenance"
    )

    mtbf = fields.Float(
        string='MTBF (Days)',
        compute='_compute_maintenance_stats',
        store=False,
        help="Mean Time Between Failures - average days between corrective maintenance requests"
    )

    # ==========================================================================
    # COMPUTE METHODS
    # ==========================================================================

    @api.depends('name')  # TODO: Change to 'request_ids', 'request_ids.stage'
    def _compute_request_counts(self):
        """
        Compute total and open request counts for smart button.

        IMPLEMENTATION:
        ---------------
        1. request_count: Count all requests linked to this equipment
        2. open_request_count: Count requests where stage NOT IN ('repaired', 'scrap')

        Example:
        ```python
        for equipment in self:
            requests = self.env['maintenance.request'].search([
                ('equipment_id', '=', equipment.id)
            ])
            equipment.request_count = len(requests)
            equipment.open_request_count = len(requests.filtered(
                lambda r: r.stage not in ('repaired', 'scrap')
            ))
        ```
        """
        # TODO: Implement actual count logic
        for equipment in self:
            equipment.request_count = 0
            equipment.open_request_count = 0

    @api.depends('warranty_date')
    def _compute_warranty_alert(self):
        """
        Compute warranty alert status and days to expiration.

        IMPLEMENTATION:
        ---------------
        1. Calculate days until warranty_date
        2. Set warranty_alert = True if <= 30 days remaining
        3. Set warranty_state based on days remaining:
           - 'valid': > 30 days
           - 'expiring': 1-30 days
           - 'expired': <= 0 days
           - 'none': no warranty_date set

        ALERT THRESHOLDS:
        - Red alert: <= 7 days (critical)
        - Yellow alert: 8-30 days (warning)
        - Green: > 30 days (ok)
        """
        today = fields.Date.today()
        for equipment in self:
            if not equipment.warranty_date:
                equipment.warranty_alert = False
                equipment.days_to_warranty_end = 0
                equipment.warranty_state = 'none'
            else:
                delta = (equipment.warranty_date - today).days
                equipment.days_to_warranty_end = delta
                equipment.warranty_alert = delta <= 30
                if delta <= 0:
                    equipment.warranty_state = 'expired'
                elif delta <= 30:
                    equipment.warranty_state = 'expiring'
                else:
                    equipment.warranty_state = 'valid'

    @api.depends('name')  # TODO: Change to 'request_ids', 'request_ids.cost_total', etc.
    def _compute_maintenance_stats(self):
        """
        Compute maintenance statistics for equipment history.

        IMPLEMENTATION:
        ---------------
        1. total_maintenance_cost: SUM of request.cost_total
        2. total_downtime: SUM of request.duration
        3. last_maintenance_date: MAX of request.close_date where stage='repaired'
        4. mtbf: Calculate Mean Time Between Failures

        MTBF CALCULATION:
        ```python
        # Get all corrective maintenance requests sorted by date
        corrective_requests = requests.filtered(
            lambda r: r.maintenance_type == 'corrective' and r.close_date
        ).sorted('close_date')

        if len(corrective_requests) > 1:
            first_date = corrective_requests[0].close_date
            last_date = corrective_requests[-1].close_date
            total_days = (last_date - first_date).days
            mtbf = total_days / (len(corrective_requests) - 1)
        ```
        """
        # TODO: Implement actual statistics calculation
        for equipment in self:
            equipment.total_maintenance_cost = 0.0
            equipment.total_downtime = 0.0
            equipment.last_maintenance_date = False
            equipment.mtbf = 0.0

    # ==========================================================================
    # ONCHANGE METHODS
    # ==========================================================================

    @api.onchange('owner_type')
    def _onchange_owner_type(self):
        """
        Clear department/employee when owner_type changes.

        IMPLEMENTATION:
        ---------------
        - If owner_type = 'department': Clear employee_id
        - If owner_type = 'employee': Clear department_id
        """
        if self.owner_type == 'department':
            self.employee_id = False
        elif self.owner_type == 'employee':
            self.department_id = False

    @api.onchange('maintenance_team_id')
    def _onchange_maintenance_team_id(self):
        """
        Reset technician when team changes (to enforce team membership).

        IMPLEMENTATION:
        ---------------
        1. Clear technician_id when team changes
        2. Optionally set technician to first team member as default
        """
        self.technician_id = False
        # Optional: Auto-select first team member
        # if self.maintenance_team_id and self.maintenance_team_id.member_ids:
        #     self.technician_id = self.maintenance_team_id.member_ids[0]

    # ==========================================================================
    # ACTION METHODS
    # ==========================================================================

    def action_view_requests(self):
        """
        SMART BUTTON ACTION - View maintenance requests for this equipment.

        This is a KEY FEATURE demonstrating Odoo "smart button" pattern.

        IMPLEMENTATION:
        ---------------
        Return action window filtered to show only requests for this equipment.

        Example:
        ```python
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Maintenance Requests'),
            'res_model': 'maintenance.request',
            'view_mode': 'tree,form,kanban,calendar',
            'domain': [('equipment_id', '=', self.id)],
            'context': {
                'default_equipment_id': self.id,
                'default_maintenance_team_id': self.maintenance_team_id.id,
                'default_technician_id': self.technician_id.id,
                'default_category_id': self.category_id.id,
            },
        }
        ```

        VIEW CONFIGURATION:
        - Button should show: icon="fa-wrench" or icon="fa-cogs"
        - Badge should show: open_request_count
        - Button type: "object" (calls this method)
        """
        self.ensure_one()
        # TODO: Implement action
        return {
            'type': 'ir.actions.act_window',
            'name': _('Maintenance Requests'),
            'res_model': 'maintenance.request',
            'view_mode': 'tree,form',
            'domain': [('equipment_id', '=', self.id)],
            'context': {
                'default_equipment_id': self.id,
            },
        }

    def action_set_scrapped(self):
        """
        Manual action to mark equipment as scrapped.

        IMPLEMENTATION:
        ---------------
        Set state='scrapped' and active=False.
        Log a message to the chatter.
        """
        for equipment in self:
            equipment.write({
                'state': 'scrapped',
                'active': False,
            })
            equipment.message_post(
                body=_("Equipment has been marked as scrapped."),
                message_type='notification'
            )

    def action_set_operational(self):
        """
        Restore equipment to operational status.
        """
        self.write({
            'state': 'operational',
            'active': True,
        })

    # ==========================================================================
    # CONSTRAINTS
    # ==========================================================================

    @api.constrains('owner_type', 'department_id', 'employee_id')
    def _check_owner(self):
        """
        Validate that owner is set correctly based on owner_type.
        """
        for equipment in self:
            if equipment.owner_type == 'department' and not equipment.department_id:
                pass  # Department is optional
            if equipment.owner_type == 'employee' and not equipment.employee_id:
                pass  # Employee is optional

    _sql_constraints = [
        ('serial_unique', 'UNIQUE(serial_number)',
         'Serial number must be unique!'),
    ]

    # ==========================================================================
    # DISPLAY NAME
    # ==========================================================================

    def name_get(self):
        """
        Display name with serial number if available.

        Example: "CNC Machine #001 [SN-12345]"
        """
        result = []
        for equipment in self:
            name = equipment.name
            if equipment.serial_number:
                name = f"{name} [{equipment.serial_number}]"
            result.append((equipment.id, name))
        return result
