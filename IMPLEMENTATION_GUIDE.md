# GearGuard Implementation Guide

## Current Status: 65% Ready for Demo

**Last Review**: 2025-12-27

---

## File Readiness Matrix

| File | Status | Priority | Work Needed |
|------|--------|----------|-------------|
| `__init__.py` | ✅ READY | - | None |
| `__manifest__.py` | ✅ READY | - | None |
| `models/maintenance_equipment_category.py` | 🔴 TEMPLATE | HIGH | Compute + Action |
| `models/maintenance_team.py` | 🔴 TEMPLATE | HIGH | Compute + Actions |
| `models/maintenance_equipment.py` | 🟡 NEEDS WORK | HIGH | Compute methods |
| `models/maintenance_request.py` | ✅ READY | - | Core logic complete |
| `views/equipment_category_views.xml` | 🟢 MOSTLY READY | LOW | Optional smart button |
| `views/team_views.xml` | 🟡 NEEDS WORK | MEDIUM | Smart buttons |
| `views/equipment_views.xml` | 🟡 NEEDS WORK | HIGH | Uncomment sections |
| `views/request_views.xml` | ✅ READY | - | None |
| `views/menu_views.xml` | ✅ READY | - | None |
| `security/maintenance_security.xml` | ✅ READY | - | None |
| `security/ir.model.access.csv` | 🟢 MOSTLY READY | LOW | Wizard/Report access |
| `data/mail_templates.xml` | ✅ READY | - | None |
| `data/scheduled_actions.xml` | 🟡 NEEDS WORK | LOW | Cron implementations |
| `data/demo_data.xml` | ✅ READY | - | None |
| `report/maintenance_report.py` | 🟡 NEEDS WORK | LOW | SQL VIEW verify |
| `wizard/warranty_alert_wizard.py` | 🟡 NEEDS WORK | LOW | Email sending |
| `static/src/css/maintenance.css` | ✅ READY | - | None |

---

## Implementation Phases

### Phase 1: Core Model Compute Methods (HIGH PRIORITY)

**Goal**: Get all computed fields working so views display correct data.

#### 1.1 Equipment Category - `models/maintenance_equipment_category.py`

**File**: `/home/Ahad/gearguard/models/maintenance_equipment_category.py`

**Tasks**:
1. **Line 79-85**: Uncomment `equipment_ids` One2many field
2. **Line 102**: Change `@api.depends('name')` to `@api.depends('equipment_ids')`
3. **Line 124-126**: Implement `_compute_equipment_count()`:
```python
def _compute_equipment_count(self):
    equipment_data = self.env['maintenance.equipment'].read_group(
        domain=[('category_id', 'in', self.ids), ('active', '=', True)],
        fields=['category_id'],
        groupby=['category_id']
    )
    mapped_data = {x['category_id'][0]: x['category_id_count'] for x in equipment_data}
    for category in self:
        category.equipment_count = mapped_data.get(category.id, 0)
```

4. **Line 152-153**: Implement `action_view_equipment()`:
```python
def action_view_equipment(self):
    self.ensure_one()
    return {
        'type': 'ir.actions.act_window',
        'name': _('Equipment'),
        'res_model': 'maintenance.equipment',
        'view_mode': 'tree,form,kanban',
        'domain': [('category_id', '=', self.id)],
        'context': {'default_category_id': self.id},
    }
```

---

#### 1.2 Maintenance Team - `models/maintenance_team.py`

**File**: `/home/Ahad/gearguard/models/maintenance_team.py`

**Tasks**:
1. **Lines 113-119**: Uncomment `request_ids` One2many field
2. **Lines 121-127**: Uncomment `equipment_ids` One2many field
3. **Line 158**: Change `@api.depends('name')` to `@api.depends('request_ids', 'request_ids.stage')`
4. **Line 198**: Change `@api.depends('name')` to `@api.depends('equipment_ids')`

5. **Lines 193-196**: Implement `_compute_request_counts()`:
```python
def _compute_request_counts(self):
    for team in self:
        requests = self.env['maintenance.request'].search([
            ('maintenance_team_id', '=', team.id),
            ('active', '=', True)
        ])
        team.open_request_count = len(requests.filtered(
            lambda r: r.stage not in ('repaired', 'scrap')
        ))
        team.new_request_count = len(requests.filtered(
            lambda r: r.stage == 'new'
        ))
```

6. **Lines 217-218**: Implement `_compute_equipment_count()`:
```python
def _compute_equipment_count(self):
    for team in self:
        team.equipment_count = self.env['maintenance.equipment'].search_count([
            ('maintenance_team_id', '=', team.id),
            ('active', '=', True)
        ])
```

7. **Lines 249-250**: Implement `action_view_requests()`:
```python
def action_view_requests(self):
    self.ensure_one()
    return {
        'type': 'ir.actions.act_window',
        'name': _('Maintenance Requests'),
        'res_model': 'maintenance.request',
        'view_mode': 'kanban,tree,form,calendar',
        'domain': [('maintenance_team_id', '=', self.id)],
        'context': {'default_maintenance_team_id': self.id},
    }
```

8. **Lines 261-262**: Implement `action_view_equipment()`:
```python
def action_view_equipment(self):
    self.ensure_one()
    return {
        'type': 'ir.actions.act_window',
        'name': _('Equipment'),
        'res_model': 'maintenance.equipment',
        'view_mode': 'tree,form,kanban',
        'domain': [('maintenance_team_id', '=', self.id)],
        'context': {'default_maintenance_team_id': self.id},
    }
```

---

#### 1.3 Maintenance Equipment - `models/maintenance_equipment.py`

**File**: `/home/Ahad/gearguard/models/maintenance_equipment.py`

**Tasks**:
1. **Lines 249-255**: Uncomment `request_ids` One2many field
2. **Line 342**: Change `@api.depends('name')` to `@api.depends('request_ids', 'request_ids.stage')`

3. **Lines 364-367**: Implement `_compute_request_counts()`:
```python
def _compute_request_counts(self):
    for equipment in self:
        requests = self.env['maintenance.request'].search([
            ('equipment_id', '=', equipment.id),
            ('active', '=', True)
        ])
        equipment.request_count = len(requests)
        equipment.open_request_count = len(requests.filtered(
            lambda r: r.stage not in ('repaired', 'scrap')
        ))
```

4. **Lines 432-437**: Implement `_compute_maintenance_stats()`:
```python
def _compute_maintenance_stats(self):
    for equipment in self:
        requests = self.env['maintenance.request'].search([
            ('equipment_id', '=', equipment.id),
            ('stage', '=', 'repaired'),
            ('active', '=', True)
        ])
        equipment.total_maintenance_cost = sum(requests.mapped('cost_total'))
        equipment.total_downtime = sum(requests.mapped('duration'))

        if requests:
            equipment.last_maintenance_date = max(requests.mapped('close_date') or [False])
            # MTBF calculation (average days between repairs)
            close_dates = sorted([r.close_date for r in requests if r.close_date])
            if len(close_dates) > 1:
                deltas = [(close_dates[i+1] - close_dates[i]).days
                          for i in range(len(close_dates)-1)]
                equipment.mtbf = sum(deltas) / len(deltas)
            else:
                equipment.mtbf = 0
        else:
            equipment.total_maintenance_cost = 0
            equipment.total_downtime = 0
            equipment.last_maintenance_date = False
            equipment.mtbf = 0
```

---

### Phase 2: View Enhancements (MEDIUM PRIORITY)

**Goal**: Enable visual features that are currently commented out.

#### 2.1 Equipment Views - `views/equipment_views.xml`

**File**: `/home/Ahad/gearguard/views/equipment_views.xml`

**Tasks**:
1. **Lines 88-97**: Uncomment the smart button `<div class="oe_button_box">` section
2. **Lines 99-100**: Uncomment state ribbon widget
3. **Lines 115-121**: Uncomment warranty alert banner

---

#### 2.2 Team Views - `views/team_views.xml`

**File**: `/home/Ahad/gearguard/views/team_views.xml`

**Tasks**:
1. **Line 84 area**: Add smart button box to form view:
```xml
<div class="oe_button_box" name="button_box">
    <button class="oe_stat_button" type="object" name="action_view_requests" icon="fa-wrench">
        <field string="Requests" name="open_request_count" widget="statinfo"/>
    </button>
    <button class="oe_stat_button" type="object" name="action_view_equipment" icon="fa-cogs">
        <field string="Equipment" name="equipment_count" widget="statinfo"/>
    </button>
</div>
```

---

### Phase 3: Security Access (LOW PRIORITY)

**Goal**: Enable access to wizard and report models.

#### 3.1 Access Rights - `security/ir.model.access.csv`

**File**: `/home/Ahad/gearguard/security/ir.model.access.csv`

**Tasks**:
1. **Lines 53-54**: Uncomment wizard access rules
2. **Lines 59-61**: Uncomment report access rules

---

### Phase 4: Enhancements (LOW PRIORITY - POST-MVP)

These can be deferred until core functionality is working.

#### 4.1 Scheduled Actions - `data/scheduled_actions.xml`

**File**: `/home/Ahad/gearguard/data/scheduled_actions.xml`

**Tasks**:
1. **Lines 67-86**: Complete warranty alerts cron implementation
2. **Lines 101-127**: Complete scheduled maintenance reminder

---

#### 4.2 Warranty Wizard - `wizard/warranty_alert_wizard.py`

**File**: `/home/Ahad/gearguard/wizard/warranty_alert_wizard.py`

**Tasks**:
1. **Lines 189-211**: Implement actual email sending in `action_send_alerts()`:
```python
if self.template_id:
    for equipment in self.equipment_ids:
        self.template_id.send_mail(equipment.id, force_send=True)
```

---

#### 4.3 Maintenance Report - `report/maintenance_report.py`

**File**: `/home/Ahad/gearguard/report/maintenance_report.py`

**Tasks**:
1. Verify SQL VIEW works correctly after models are complete
2. Test pivot/graph views display properly

---

## Implementation Checklist

### Critical Path (Must Complete)
- [ ] Phase 1.1: Equipment Category compute methods
- [ ] Phase 1.2: Team compute methods and actions
- [ ] Phase 1.3: Equipment compute methods
- [ ] Phase 2.1: Uncomment equipment view sections
- [ ] Phase 2.2: Add team smart buttons

### Already Complete (No Action Needed)
- [x] `maintenance_request.py` - All business logic implemented
  - Auto-fill onchange ✓
  - Scrap logic ✓
  - Cost calculations ✓
  - Overdue detection ✓
- [x] `request_views.xml` - Full kanban, calendar, form, pivot, graph
- [x] `menu_views.xml` - Complete menu structure
- [x] `maintenance_security.xml` - All groups and rules
- [x] `demo_data.xml` - 7 equipment, 6 requests, 4 teams
- [x] `mail_templates.xml` - 3 email templates
- [x] `maintenance.css` - All styling with animations

### Deferred (Post-MVP)
- [ ] Phase 3: Security access for wizard/report
- [ ] Phase 4.1: Scheduled action implementations
- [ ] Phase 4.2: Warranty wizard email sending
- [ ] Phase 4.3: Report SQL VIEW verification

---

## Estimated Effort

| Phase | Effort | Files Changed |
|-------|--------|---------------|
| Phase 1.1 | 30 min | 1 file |
| Phase 1.2 | 45 min | 1 file |
| Phase 1.3 | 45 min | 1 file |
| Phase 2.1 | 15 min | 1 file |
| Phase 2.2 | 15 min | 1 file |
| **Total Critical** | **~2.5 hours** | **5 files** |

---

## Demo Features Already Working

1. **Kanban Drag-Drop** - Request cards move between stages
2. **Auto-Fill** - Equipment selection populates team/technician
3. **Scrap Logic** - Moving to scrap deactivates equipment
4. **Overdue Indicators** - Red styling on overdue cards
5. **Calendar View** - Scheduled maintenance visible
6. **Cost Tracking** - Parts + labor = total cost
7. **Warranty Alerts** - Computed but needs equipment count fix
8. **Priority Display** - Stars and color ribbons
9. **Email Templates** - Ready for sending
10. **Demo Data** - Comprehensive test scenarios

---

## Quick Start Commands

```bash
# Install module in Odoo
./odoo-bin -d your_database -i gearguard

# Update after changes
./odoo-bin -d your_database -u gearguard

# Run with demo data
./odoo-bin -d your_database -i gearguard --demo
```

---

## Files to Modify (Priority Order)

1. `/home/Ahad/gearguard/models/maintenance_equipment_category.py`
2. `/home/Ahad/gearguard/models/maintenance_team.py`
3. `/home/Ahad/gearguard/models/maintenance_equipment.py`
4. `/home/Ahad/gearguard/views/equipment_views.xml`
5. `/home/Ahad/gearguard/views/team_views.xml`
