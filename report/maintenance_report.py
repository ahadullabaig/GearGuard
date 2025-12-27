# -*- coding: utf-8 -*-
"""
Maintenance Report Model (SQL View)
====================================

This model provides an aggregated view of maintenance data for reporting.
It uses SQL VIEW for efficient querying of large datasets.

IMPLEMENTATION PRIORITY: LOW (Enhancement)
Implement after core functionality is working.

PURPOSE:
--------
- Provide aggregated maintenance statistics
- Support pivot and graph views
- Enable custom reporting queries

REPORT METRICS:
---------------
1. Requests per Team
2. Requests per Equipment Category
3. Total Duration by Team
4. Total Cost by Equipment
5. Corrective vs Preventive ratio
6. Average resolution time

SQL VIEW STRUCTURE:
------------------
The _auto = False tells Odoo not to create a table.
We define the view in init() method.

FIELDS:
-------
| Field Name        | Type      | Description                        |
|-------------------|-----------|------------------------------------|
| name              | Char      | Request name                       |
| equipment_id      | Many2one  | Equipment reference                |
| category_id       | Many2one  | Equipment category                 |
| team_id           | Many2one  | Maintenance team                   |
| technician_id     | Many2one  | Assigned technician                |
| maintenance_type  | Selection | Corrective/Preventive              |
| stage             | Selection | Request stage                      |
| request_date      | Date      | Request creation date              |
| close_date        | Date      | Request completion date            |
| duration          | Float     | Hours spent                        |
| cost_total        | Float     | Total cost                         |
| resolution_days   | Integer   | Days to resolve                    |

VIEWS NEEDED:
- Pivot view for multidimensional analysis
- Graph view for visualizations
"""

from odoo import models, fields, api, tools


class MaintenanceReport(models.Model):
    _name = 'maintenance.report'
    _description = 'Maintenance Analysis Report'
    _auto = False  # This is a SQL VIEW, not a table
    _order = 'request_date desc'

    # ==========================================================================
    # FIELDS (Read-only, mapped from SQL view)
    # ==========================================================================

    name = fields.Char(
        string='Request',
        readonly=True
    )

    equipment_id = fields.Many2one(
        comodel_name='maintenance.equipment',
        string='Equipment',
        readonly=True
    )

    category_id = fields.Many2one(
        comodel_name='maintenance.equipment.category',
        string='Category',
        readonly=True
    )

    maintenance_team_id = fields.Many2one(
        comodel_name='maintenance.team',
        string='Team',
        readonly=True
    )

    technician_id = fields.Many2one(
        comodel_name='res.users',
        string='Technician',
        readonly=True
    )

    maintenance_type = fields.Selection(
        selection=[
            ('corrective', 'Corrective'),
            ('preventive', 'Preventive'),
        ],
        string='Type',
        readonly=True
    )

    stage = fields.Selection(
        selection=[
            ('new', 'New'),
            ('in_progress', 'In Progress'),
            ('repaired', 'Repaired'),
            ('scrap', 'Scrap'),
        ],
        string='Stage',
        readonly=True
    )

    priority = fields.Selection(
        selection=[
            ('0', 'Low'),
            ('1', 'Normal'),
            ('2', 'High'),
            ('3', 'Urgent'),
        ],
        string='Priority',
        readonly=True
    )

    request_date = fields.Date(
        string='Request Date',
        readonly=True
    )

    schedule_date = fields.Date(
        string='Scheduled Date',
        readonly=True
    )

    close_date = fields.Date(
        string='Close Date',
        readonly=True
    )

    duration = fields.Float(
        string='Duration (Hours)',
        readonly=True,
        group_operator='sum'
    )

    cost_parts = fields.Float(
        string='Parts Cost',
        readonly=True,
        group_operator='sum'
    )

    cost_labor = fields.Float(
        string='Labor Cost',
        readonly=True,
        group_operator='sum'
    )

    cost_total = fields.Float(
        string='Total Cost',
        readonly=True,
        group_operator='sum'
    )

    resolution_days = fields.Integer(
        string='Resolution Days',
        readonly=True,
        group_operator='avg',
        help="Days between request date and close date"
    )

    request_count = fields.Integer(
        string='# Requests',
        readonly=True,
        group_operator='sum'
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        readonly=True
    )

    # ==========================================================================
    # SQL VIEW DEFINITION
    # ==========================================================================

    def init(self):
        """
        Create SQL VIEW for maintenance reporting.

        IMPLEMENTATION:
        ---------------
        This method is called when the module is installed/updated.
        It drops any existing view and creates a new one.

        The SQL query joins maintenance.request with equipment and category
        to provide denormalized data for efficient reporting.
        """
        tools.drop_view_if_exists(self.env.cr, self._table)

        # TODO: Implement actual SQL VIEW
        # For now, create a simple view
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    r.id AS id,
                    r.name AS name,
                    r.equipment_id AS equipment_id,
                    e.category_id AS category_id,
                    r.maintenance_team_id AS maintenance_team_id,
                    r.technician_id AS technician_id,
                    r.maintenance_type AS maintenance_type,
                    r.stage AS stage,
                    r.priority AS priority,
                    r.request_date AS request_date,
                    r.schedule_date AS schedule_date,
                    r.close_date AS close_date,
                    r.duration AS duration,
                    r.cost_parts AS cost_parts,
                    r.cost_labor AS cost_labor,
                    r.cost_total AS cost_total,
                    CASE
                        WHEN r.close_date IS NOT NULL AND r.request_date IS NOT NULL
                        THEN r.close_date - r.request_date
                        ELSE NULL
                    END AS resolution_days,
                    1 AS request_count,
                    r.company_id AS company_id
                FROM
                    maintenance_request r
                LEFT JOIN
                    maintenance_equipment e ON r.equipment_id = e.id
                WHERE
                    r.active = TRUE
            )
        """ % self._table)

    # ==========================================================================
    # Additional methods for custom reporting can be added here
    # ==========================================================================

    @api.model
    def get_maintenance_summary(self, domain=None):
        """
        Get summary statistics for maintenance requests.

        Returns dict with:
        - total_requests
        - total_duration
        - total_cost
        - avg_resolution_time
        - corrective_count
        - preventive_count
        """
        domain = domain or []
        requests = self.search(domain)

        return {
            'total_requests': len(requests),
            'total_duration': sum(requests.mapped('duration')),
            'total_cost': sum(requests.mapped('cost_total')),
            'avg_resolution_time': (
                sum(r.resolution_days or 0 for r in requests) / len(requests)
                if requests else 0
            ),
            'corrective_count': len(requests.filtered(lambda r: r.maintenance_type == 'corrective')),
            'preventive_count': len(requests.filtered(lambda r: r.maintenance_type == 'preventive')),
        }
