# -*- coding: utf-8 -*-
"""
Maintenance Team Model
======================

This model represents maintenance teams - groups of technicians who handle
maintenance requests. Teams are assigned to equipment and requests.

IMPLEMENTATION PRIORITY: HIGH (Step 1 - Foundation)
This model must be implemented BEFORE Equipment, as Equipment references it.

BUSINESS LOGIC:
---------------
- Each team has multiple members (technicians)
- Teams are assigned as default handlers for specific equipment
- When a request is created, the team from equipment is auto-filled
- Workflow Logic: Only team members should pick up requests for their team

FIELDS TO IMPLEMENT:
--------------------
| Field Name          | Type     | Required | Description                           |
|---------------------|----------|----------|---------------------------------------|
| name                | Char     | YES      | Team name (e.g., "Mechanics")         |
| color               | Integer  | NO       | Color index for Kanban (0-11)         |
| active              | Boolean  | NO       | Archive flag (default: True)          |
| company_id          | Many2one | NO       | Multi-company support                 |
| member_ids          | Many2many| NO       | Team members (res.users)              |
| request_ids         | One2many | COMPUTED | Related maintenance requests          |
| open_request_count  | Integer  | COMPUTED | Count of open (non-closed) requests   |
| equipment_count     | Integer  | COMPUTED | Count of equipment assigned to team   |
| todo_request_ids    | One2many | COMPUTED | Requests in 'new' stage               |
| todo_request_count  | Integer  | COMPUTED | Count of 'new' requests               |

METHODS TO IMPLEMENT:
--------------------
1. _compute_open_request_count() - Count requests not in 'repaired'/'scrap' stage
2. _compute_equipment_count() - Count equipment assigned to this team
3. _compute_todo_request_count() - Count requests in 'new' stage (dashboard)

RELATIONSHIPS:
-------------
- Many2many to res.users (member_ids)
- One2many to maintenance.equipment (inverse of maintenance_team_id)
- One2many to maintenance.request (inverse of maintenance_team_id)

VIEWS NEEDED: (in team_views.xml)
- Form view: Team details with member list (many2many_tags)
- Tree view: Team listing with counts
- Kanban view: Team cards showing open requests badge

SECURITY CONSIDERATIONS:
- Team managers should be able to see all team requests
- Technicians should only see requests assigned to their team(s)

DEMO DATA NEEDED:
- "Mechanics" (members: user_mechanic_1, user_mechanic_2)
- "IT Support" (members: user_it_1, user_it_2)
- "Electricians" (members: user_electrician_1)
"""

from odoo import models, fields, api, _


class MaintenanceTeam(models.Model):
    _name = 'maintenance.team'
    _description = 'Maintenance Team'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    # ==========================================================================
    # BASIC FIELDS
    # ==========================================================================

    name = fields.Char(
        string='Team Name',
        required=True,
        tracking=True,
        help="Name of the maintenance team (e.g., Mechanics, IT Support, Electricians)"
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help="If unchecked, the team will be hidden but not deleted."
    )

    color = fields.Integer(
        string='Color',
        default=0,
        help="Color index for Kanban view (0-11)"
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
        help="Company this team belongs to (for multi-company setups)"
    )

    # ==========================================================================
    # RELATIONAL FIELDS
    # ==========================================================================

    member_ids = fields.Many2many(
        comodel_name='res.users',
        relation='maintenance_team_users_rel',
        column1='team_id',
        column2='user_id',
        string='Team Members',
        help="Users who are part of this maintenance team (technicians)"
    )

    # TODO: Uncomment after maintenance.request is implemented
    # request_ids = fields.One2many(
    #     comodel_name='maintenance.request',
    #     inverse_name='maintenance_team_id',
    #     string='Maintenance Requests',
    #     help="All maintenance requests assigned to this team"
    # )

    # TODO: Uncomment after maintenance.equipment is implemented
    # equipment_ids = fields.One2many(
    #     comodel_name='maintenance.equipment',
    #     inverse_name='maintenance_team_id',
    #     string='Equipment',
    #     help="Equipment assigned to this team for maintenance"
    # )

    # ==========================================================================
    # COMPUTED FIELDS
    # ==========================================================================

    open_request_count = fields.Integer(
        string='Open Requests',
        compute='_compute_request_counts',
        store=False,
        help="Number of open maintenance requests (not repaired/scrapped)"
    )

    todo_request_count = fields.Integer(
        string='New Requests',
        compute='_compute_request_counts',
        store=False,
        help="Number of requests in 'New' stage waiting to be picked up"
    )

    equipment_count = fields.Integer(
        string='Equipment Count',
        compute='_compute_equipment_count',
        store=False,
        help="Number of equipment items assigned to this team"
    )

    # ==========================================================================
    # COMPUTE METHODS
    # ==========================================================================

    @api.depends('name')  # TODO: Change to 'request_ids', 'request_ids.stage'
    def _compute_request_counts(self):
        """
        Compute open request count and todo (new) request count.

        IMPLEMENTATION:
        ---------------
        1. open_request_count: Count requests where stage NOT IN ('repaired', 'scrap')
        2. todo_request_count: Count requests where stage = 'new'

        Example implementation:
        ```python
        for team in self:
            requests = self.env['maintenance.request'].search([
                ('maintenance_team_id', '=', team.id)
            ])
            team.open_request_count = len(requests.filtered(
                lambda r: r.stage not in ('repaired', 'scrap')
            ))
            team.todo_request_count = len(requests.filtered(
                lambda r: r.stage == 'new'
            ))
        ```

        PERFORMANCE TIP:
        Use read_group for better performance with large datasets:
        ```python
        request_data = self.env['maintenance.request'].read_group(
            domain=[('maintenance_team_id', 'in', self.ids)],
            fields=['maintenance_team_id', 'stage'],
            groupby=['maintenance_team_id', 'stage'],
            lazy=False
        )
        ```
        """
        # TODO: Implement actual count logic
        for team in self:
            team.open_request_count = 0  # Placeholder
            team.todo_request_count = 0  # Placeholder

    @api.depends('name')  # TODO: Change to 'equipment_ids'
    def _compute_equipment_count(self):
        """
        Compute the number of equipment assigned to this team.

        IMPLEMENTATION:
        ---------------
        Count active equipment where maintenance_team_id = this team.

        Example:
        ```python
        for team in self:
            team.equipment_count = self.env['maintenance.equipment'].search_count([
                ('maintenance_team_id', '=', team.id),
                ('active', '=', True)
            ])
        ```
        """
        # TODO: Implement actual count logic
        for team in self:
            team.equipment_count = 0  # Placeholder

    # ==========================================================================
    # ACTION METHODS
    # ==========================================================================

    def action_view_requests(self):
        """
        Smart button action to view all requests for this team.

        IMPLEMENTATION:
        ---------------
        Return action window showing requests filtered by this team.

        Example:
        ```python
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Maintenance Requests'),
            'res_model': 'maintenance.request',
            'view_mode': 'kanban,tree,form,calendar',
            'domain': [('maintenance_team_id', '=', self.id)],
            'context': {
                'default_maintenance_team_id': self.id,
                'search_default_todo': 1,  # Pre-filter to show new requests
            },
        }
        ```
        """
        # TODO: Implement action
        self.ensure_one()
        return {}

    def action_view_equipment(self):
        """
        Smart button action to view equipment assigned to this team.

        IMPLEMENTATION:
        ---------------
        Return action window showing equipment filtered by this team.
        """
        # TODO: Implement action
        self.ensure_one()
        return {}

    # ==========================================================================
    # HELPER METHODS
    # ==========================================================================

    def _get_team_members_domain(self):
        """
        Get domain to filter users who are members of this team.
        Useful for domain filters in views.

        Returns:
            list: Domain for res.users filtering
        """
        self.ensure_one()
        return [('id', 'in', self.member_ids.ids)]

    # ==========================================================================
    # CONSTRAINTS
    # ==========================================================================

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name, company_id)',
         'Team name must be unique per company!'),
    ]
