# -*- coding: utf-8 -*-
"""
Maintenance Equipment Category Model
====================================

This model provides categorization for equipment/assets in the maintenance system.
Categories help organize equipment by type (e.g., Machinery, Vehicles, IT Equipment).

IMPLEMENTATION PRIORITY: HIGH (Step 1 - Foundation)
This model must be implemented FIRST as Equipment depends on it.

FIELDS TO IMPLEMENT:
--------------------
| Field Name       | Type    | Required | Description                              |
|------------------|---------|----------|------------------------------------------|
| name             | Char    | YES      | Category name (e.g., "CNC Machines")     |
| color            | Integer | NO       | Color index for Kanban views (0-11)      |
| equipment_count  | Integer | COMPUTED | Number of equipment in this category     |
| note             | Text    | NO       | Optional description/notes               |

METHODS TO IMPLEMENT:
--------------------
1. _compute_equipment_count()
   - Counts equipment records linked to this category
   - Used for smart button badge display

RELATIONSHIPS:
-------------
- One2many to maintenance.equipment (inverse of category_id)

VIEWS NEEDED: (in equipment_category_views.xml)
- Form view: Simple form with name, color picker, notes
- Tree view: List with name and equipment count
- Kanban view: Cards with color coding

DEMO DATA NEEDED:
- "Machinery" (color: 1)
- "Vehicles" (color: 2)
- "IT Equipment" (color: 3)
- "HVAC Systems" (color: 4)
- "Office Equipment" (color: 5)
"""

from odoo import models, fields, api


class MaintenanceEquipmentCategory(models.Model):
    _name = 'maintenance.equipment.category'
    _description = 'Maintenance Equipment Category'
    _order = 'name'

    # ==========================================================================
    # BASIC FIELDS
    # ==========================================================================

    name = fields.Char(
        string='Category Name',
        required=True,
        translate=True,
        help="Name of the equipment category (e.g., Machinery, Vehicles, IT Equipment)"
    )

    color = fields.Integer(
        string='Color',
        default=0,
        help="Color index for Kanban view (0-11). Used for visual distinction."
    )

    note = fields.Text(
        string='Notes',
        translate=True,
        help="Additional notes or description for this category"
    )

    # ==========================================================================
    # RELATIONAL FIELDS
    # ==========================================================================

    # TODO: Uncomment after maintenance.equipment is implemented
    # equipment_ids = fields.One2many(
    #     comodel_name='maintenance.equipment',
    #     inverse_name='category_id',
    #     string='Equipment',
    #     help="List of equipment belonging to this category"
    # )

    # ==========================================================================
    # COMPUTED FIELDS
    # ==========================================================================

    equipment_count = fields.Integer(
        string='Equipment Count',
        compute='_compute_equipment_count',
        store=False,
        help="Number of equipment items in this category"
    )

    # ==========================================================================
    # COMPUTE METHODS
    # ==========================================================================

    @api.depends('name')  # TODO: Change to depends on equipment_ids after implementation
    def _compute_equipment_count(self):
        """
        Compute the number of equipment in each category.

        IMPLEMENTATION:
        ---------------
        1. Use read_group for efficiency with large datasets
        2. Count only active equipment (active=True)

        Example implementation:
        ```python
        equipment_data = self.env['maintenance.equipment'].read_group(
            domain=[('category_id', 'in', self.ids), ('active', '=', True)],
            fields=['category_id'],
            groupby=['category_id']
        )
        mapped_data = {data['category_id'][0]: data['category_id_count'] for data in equipment_data}
        for category in self:
            category.equipment_count = mapped_data.get(category.id, 0)
        ```
        """
        # TODO: Implement actual count logic
        for category in self:
            category.equipment_count = 0  # Placeholder

    # ==========================================================================
    # ACTION METHODS
    # ==========================================================================

    def action_view_equipment(self):
        """
        Smart button action to view equipment in this category.

        IMPLEMENTATION:
        ---------------
        Return an action window that shows equipment filtered by this category.

        Example:
        ```python
        return {
            'type': 'ir.actions.act_window',
            'name': _('Equipment'),
            'res_model': 'maintenance.equipment',
            'view_mode': 'kanban,tree,form',
            'domain': [('category_id', '=', self.id)],
            'context': {'default_category_id': self.id},
        }
        ```
        """
        # TODO: Implement action
        pass

    # ==========================================================================
    # CRUD OVERRIDES (if needed)
    # ==========================================================================

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Category name must be unique!'),
    ]
