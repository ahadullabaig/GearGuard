# -*- coding: utf-8 -*-
{
    'name': 'GearGuard - Maintenance Tracker',
    'version': '17.0.1.0.0',
    'category': 'Maintenance',
    'summary': 'Ultimate Equipment Maintenance Management System',
    'description': """
GearGuard: The Ultimate Maintenance Tracker
============================================

A comprehensive maintenance management system that allows companies to:
- Track assets (machines, vehicles, computers)
- Manage maintenance requests
- Schedule preventive maintenance
- Track maintenance costs
- Monitor warranty expirations
- Analyze maintenance statistics

Key Features:
- Equipment tracking by department or employee
- Maintenance team management
- Corrective and preventive maintenance workflows
- Smart auto-fill when creating requests
- Kanban board with drag-and-drop
- Calendar view for scheduled maintenance
- Cost tracking and analytics
- Warranty expiry alerts
- Maintenance history and statistics
    """,
    'author': 'GearGuard Team',
    'website': 'https://gearguard.example.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'hr',
    ],
    'data': [
        # Security
        'security/maintenance_security.xml',
        'security/ir.model.access.csv',
        # Views
        'views/equipment_category_views.xml',
        'views/team_views.xml',
        'views/equipment_views.xml',
        'views/request_views.xml',
        'views/menu_views.xml',
        # Data
        'data/mail_templates.xml',
        'data/scheduled_actions.xml',
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'gearguard/static/src/css/maintenance.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 1,
}
