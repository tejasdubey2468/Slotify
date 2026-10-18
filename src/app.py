"""
Slotify 🗓️ — Main Application & REST API Controller
Smart College Timetable Management & Scheduling Platform
"""

import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file

import database
import scheduler
import exporter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__, template_folder=TEMPLATE_DIR)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'slotify-academic-key-2026')

# Ensure database is initialized at startup
database.init_db()

# In-memory cached active timetable (synced with DB)
active_timetable = None


def get_current_active_timetable():
    """Retrieve active timetable from memory or fetch latest from database."""
    global active_timetable
    if active_timetable is None:
        latest = database.get_latest_timetable()
        if latest and 'timetable_data' in latest:
            active_timetable = latest['timetable_data']
        else:
            # Generate initial default schedule if empty
            ctx = database.get_scheduling_context()
            data, conflicts = scheduler.generate_schedules_csp(ctx)
            if data:
                active_timetable = data
                database.save_timetable("Initial Approved Schedule", "ALL", data, len(conflicts), is_published=1, is_demo=1)
                database.save_timetable_version("Initial Approved Schedule", "ALL", data, len(conflicts), status='Published', change_summary='Initial auto-generation on platform startup', is_demo=1)
    return active_timetable


# ═════════════════════════════════════════════════════════
# WEB PAGES
# ═════════════════════════════════════════════════════════
@app.route('/')
def index():
    """Render main Slotify single-page application."""
    return render_template('index.html')


# ═════════════════════════════════════════════════════════
# DASHBOARD & OVERVIEW
# ═════════════════════════════════════════════════════════
@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Return platform KPI metrics and analytical summaries."""
    stats = database.get_dashboard_stats()
    tt = get_current_active_timetable()
    if tt:
        conflicts = scheduler.detect_conflicts(tt)
        stats['active_conflicts'] = len(conflicts)
        stats['active_errors'] = len([c for c in conflicts if c.get('severity') == 'error'])
        stats['active_warnings'] = len([c for c in conflicts if c.get('severity') == 'warning'])
    else:
        stats['active_conflicts'] = 0
        stats['active_errors'] = 0
        stats['active_warnings'] = 0
    return jsonify({'status': 'ok', 'data': stats})


# ═════════════════════════════════════════════════════════
# DEPARTMENTS & ACADEMIC YEARS
# ═════════════════════════════════════════════════════════
@app.route('/api/departments', methods=['GET'])
def list_departments():
    return jsonify({'status': 'ok', 'data': database.get_departments()})

@app.route('/api/departments', methods=['POST'])
def create_department():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    code = data.get('code', '').strip()
    if not name or not code:
        return jsonify({'error': 'Department name and code are required.'}), 400
    try:
        new_id = database.add_department(name, code, data.get('hod_name', ''))
        return jsonify({'status': 'ok', 'id': new_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/academic_years', methods=['GET'])
def list_academic_years():
    return jsonify({'status': 'ok', 'data': database.get_academic_years()})

@app.route('/api/academic_years', methods=['POST'])
def create_academic_year():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    code = data.get('code', '').strip()
    year_num = data.get('year_number')
    if not name or not code or not year_num:
        return jsonify({'error': 'Name, code, and year number are required.'}), 400
    try:
        new_id = database.add_academic_year(name, code, year_num, data.get('department_id', 1))
        return jsonify({'status': 'ok', 'id': new_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# ═════════════════════════════════════════════════════════
# DIVISIONS & BATCHES MANAGEMENT (REQUIREMENT 2E)
# ═════════════════════════════════════════════════════════
@app.route('/api/divisions', methods=['GET'])
def list_divisions():
    return jsonify({'status': 'ok', 'data': database.get_divisions()})

@app.route('/api/divisions/<int:div_id>', methods=['GET'])
def get_division(div_id):
    d = database.get_division(div_id)
    if not d:
        return jsonify({'error': 'Division not found.'}), 404
    return jsonify({'status': 'ok', 'data': d})

@app.route('/api/divisions', methods=['POST'])
def create_division():
    data = request.get_json() or {}
    if not data.get('name') or not data.get('academic_year_id'):
        return jsonify({'error': 'Division name and academic year are required.'}), 400
    try:
        new_id = database.add_division(data)
        database.add_notification(f"Division Created: {data['name']}", f"Division '{data['name']}' added with batch partitioning.", "system", "#setup")
        return jsonify({'status': 'ok', 'id': new_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/divisions/<int:div_id>', methods=['PUT'])
def update_division(div_id):
    data = request.get_json() or {}
    if not data.get('name') or not data.get('academic_year_id'):
        return jsonify({'error': 'Division name and academic year are required.'}), 400
    try:
        database.update_division(div_id, data)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/divisions/<int:div_id>', methods=['DELETE'])
def delete_division(div_id):
    try:
        database.delete_division(div_id)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# ═════════════════════════════════════════════════════════
# SUBJECTS MANAGEMENT (REQUIREMENT 2C)
# ═════════════════════════════════════════════════════════
@app.route('/api/subjects', methods=['GET'])
def list_subjects():
    subjects = database.get_subjects()
    year_filter = request.args.get('year')
    if year_filter:
        subjects = [s for s in subjects if s.get('year_code') == year_filter]
    return jsonify({'status': 'ok', 'data': subjects})

@app.route('/api/subjects/<int:sub_id>', methods=['GET'])
def get_subject(sub_id):
    s = database.get_subject(sub_id)
    if not s:
        return jsonify({'error': 'Subject not found.'}), 404
    return jsonify({'status': 'ok', 'data': s})

@app.route('/api/subjects', methods=['POST'])
def create_subject():
    data = request.get_json() or {}
    if not data.get('name') or not data.get('code'):
        return jsonify({'error': 'Subject name and code are required.'}), 400
    try:
        new_id = database.add_subject(data)
        database.add_notification(f"Subject Added: {data['code']}", f"New subject '{data['name']}' added to curriculum.", "system", "#subjects")
        return jsonify({'status': 'ok', 'id': new_id})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/subjects/<int:sub_id>', methods=['PUT'])
def update_subject(sub_id):
    data = request.get_json() or {}
    if not data.get('name') or not data.get('code'):
        return jsonify({'error': 'Subject name and code are required.'}), 400
    try:
        database.update_subject(sub_id, data)
        return jsonify({'status': 'ok'})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/subjects/<int:sub_id>', methods=['DELETE'])
def delete_subject(sub_id):
    try:
        database.delete_subject(sub_id)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ═════════════════════════════════════════════════════════
# CLASSROOMS & LABORATORIES (REQUIREMENT 2D)
# ═════════════════════════════════════════════════════════
@app.route('/api/classrooms', methods=['GET'])
def list_classrooms():
    return jsonify({'status': 'ok', 'data': database.get_classrooms()})

@app.route('/api/classrooms/<int:room_id>', methods=['GET'])
def get_classroom(room_id):
    r = database.get_classroom(room_id)
    if not r:
        return jsonify({'error': 'Room not found.'}), 404
    return jsonify({'status': 'ok', 'data': r})

@app.route('/api/classrooms', methods=['POST'])
def create_classroom():
    data = request.get_json() or {}
    if not data.get('name') or not data.get('room_number'):
        return jsonify({'error': 'Room name and number are required.'}), 400
    try:
        new_id = database.add_classroom(data)
        return jsonify({'status': 'ok', 'id': new_id})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/classrooms/<int:room_id>', methods=['PUT'])
def update_classroom(room_id):
    data = request.get_json() or {}
    if not data.get('name') or not data.get('room_number'):
        return jsonify({'error': 'Room name and number are required.'}), 400
    try:
        database.update_classroom(room_id, data)
        return jsonify({'status': 'ok'})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/classrooms/<int:room_id>', methods=['DELETE'])
def delete_classroom(room_id):
    try:
        database.delete_classroom(room_id)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/classroom/<room_number>/timetable', methods=['GET'])
def get_classroom_timetable(room_number):
    tt = get_current_active_timetable()
    if not tt:
        return jsonify({'error': 'No active timetable found.'}), 404
    data = scheduler.get_classroom_timetable(tt, room_number)
    return jsonify({'status': 'ok', 'data': data})


# ═════════════════════════════════════════════════════════
# TEACHERS & FACULTY MANAGEMENT (REQUIREMENT 2B)
# ═════════════════════════════════════════════════════════
@app.route('/api/teachers', methods=['GET'])
def list_teachers():
    include_inactive = request.args.get('all') == '1'
    return jsonify({'status': 'ok', 'data': database.get_teachers(include_inactive)})

@app.route('/api/teachers/<int:teacher_id>', methods=['GET'])
def get_teacher(teacher_id):
    t = database.get_teacher(teacher_id)
    if not t:
        return jsonify({'error': 'Teacher not found'}), 404
    return jsonify({'status': 'ok', 'data': t})

@app.route('/api/teachers', methods=['POST'])
def create_teacher():
    data = request.get_json() or {}
    if not data.get('name') or not data.get('initials'):
        return jsonify({'error': 'Name and initials are required.'}), 400
    try:
        new_id = database.add_teacher(data)
        database.add_notification(f"Faculty Onboarded: {data['name']}", f"Profile created for {data['name']} ({data['initials']}).", "system", "#faculty")
        return jsonify({'status': 'ok', 'id': new_id})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/teachers/<int:teacher_id>', methods=['PUT'])
def update_teacher(teacher_id):
    data = request.get_json() or {}
    if not data.get('name') or not data.get('initials'):
        return jsonify({'error': 'Name and initials are required.'}), 400
    try:
        database.update_teacher(teacher_id, data)
        return jsonify({'status': 'ok'})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/teachers/<int:teacher_id>/check_delete', methods=['GET'])
def check_teacher_delete(teacher_id):
    """Check if faculty member has assigned courses or lectures before deletion."""
    check = database.check_teacher_assignments(teacher_id)
    if not check['exists']:
        return jsonify({'error': 'Teacher not found.'}), 404
    return jsonify({'status': 'ok', 'data': check})

@app.route('/api/teachers/<int:teacher_id>', methods=['DELETE'])
def delete_teacher(teacher_id):
    """Delete faculty member with safety check or force delete option."""
    force = request.args.get('force') == '1' or request.args.get('force') == 'true'
    check = database.check_teacher_assignments(teacher_id)

    if not check['exists']:
        return jsonify({'error': 'Teacher not found.'}), 404

    if not force and check['assigned_subjects_count'] > 0:
        return jsonify({
            'warning': f"Faculty member '{check['name']}' has {check['assigned_subjects_count']} active subject assignment(s). Please confirm deletion to automatically reassign or remove lectures.",
            'requires_confirmation': True,
            'assigned_subjects': check['subjects']
        }), 409

    try:
        database.delete_teacher(teacher_id, force=force)
        return jsonify({'status': 'ok', 'message': f"Faculty member '{check['name']}' removed successfully."})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ═════════════════════════════════════════════════════════
# FACULTY DIRECTORY & INDIVIDUAL TIMETABLES
# ═════════════════════════════════════════════════════════
@app.route('/api/faculty/timetables', methods=['GET'])
def get_all_faculty_timetables():
    teachers = database.get_teachers()
    tt = get_current_active_timetable()
    result = []
    for t in teachers:
        summary = scheduler.get_faculty_timetable(tt, t['initials']) if tt else {'total_hours': 0, 'divisions': [], 'subjects': [], 'rooms': []}
        result.append({
            'id': t['id'],
            'faculty_id': t.get('faculty_id', f"FAC-{t['initials']}"),
            'name': t['name'],
            'initials': t['initials'],
            'designation': t['designation'],
            'email': t['email'],
            'time_slot': t['time_slot'],
            'max_hours_per_week': t['max_hours_per_week'],
            'max_hours_per_day': t.get('max_hours_per_day', 6),
            'scheduled_hours': summary.get('total_hours', 0),
            'years': summary.get('divisions', []),
            'subjects': summary.get('subjects', []),
            'rooms': summary.get('rooms', []),
            'assignments': t.get('assignments', [])
        })
    return jsonify({'status': 'ok', 'data': result})

@app.route('/api/faculty/<initials>/timetable', methods=['GET'])
def get_single_faculty_timetable(initials):
    tt = get_current_active_timetable()
    if not tt:
        return jsonify({'error': 'No active timetable found.'}), 404
    data = scheduler.get_faculty_timetable(tt, initials)
    return jsonify({'status': 'ok', 'data': data})


# ═════════════════════════════════════════════════════════
# TIME SLOTS & WORKING DAYS
# ═════════════════════════════════════════════════════════
@app.route('/api/time_slots', methods=['GET'])
def list_time_slots():
    return jsonify({'status': 'ok', 'data': database.get_time_slots()})

@app.route('/api/time_slots/<int:slot_id>', methods=['PUT'])
def update_time_slot(slot_id):
    data = request.get_json() or {}
    database.update_time_slot(slot_id, data)
    return jsonify({'status': 'ok'})

@app.route('/api/working_days', methods=['GET'])
def list_working_days():
    return jsonify({'status': 'ok', 'data': database.get_working_days()})

@app.route('/api/working_days/<int:day_id>', methods=['PUT'])
def update_working_day(day_id):
    data = request.get_json() or {}
    is_working = data.get('is_working', True)
    database.update_working_day(day_id, is_working)
    return jsonify({'status': 'ok'})


# ═════════════════════════════════════════════════════════
# ACADEMIC CALENDAR & HOLIDAYS
# ═════════════════════════════════════════════════════════
@app.route('/api/holidays', methods=['GET'])
def list_holidays():
    return jsonify({'status': 'ok', 'data': database.get_holidays()})

@app.route('/api/holidays', methods=['POST'])
def create_holiday():
    data = request.get_json() or {}
    if not data.get('name') or not data.get('date'):
        return jsonify({'error': 'Name and date are required.'}), 400
    try:
        new_id = database.add_holiday(data)
        database.add_notification(f"Holiday Added: {data['name']}", f"Official holiday scheduled for {data['date']}.", "holiday", "#calendar")
        return jsonify({'status': 'ok', 'id': new_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/holidays/<int:holiday_id>', methods=['DELETE'])
def delete_holiday(holiday_id):
    database.delete_holiday(holiday_id)
    return jsonify({'status': 'ok'})


# ═════════════════════════════════════════════════════════
# TIMETABLE GENERATION & CONFLICT DETECTION (REQUIREMENT 5 & 6)
# ═════════════════════════════════════════════════════════
@app.route('/api/generate', methods=['POST'])
def generate_timetable():
    """Run full CSP constraint-solving generation across all classes/divisions."""
    global active_timetable
    ctx = database.get_scheduling_context()

    if not ctx.get('teachers'):
        return jsonify({'error': 'No faculty records found. Please add faculty in Academic Setup.'}), 400

    # Execute CSP solver, passing any existing locked timetable cells
    data, conflicts = scheduler.generate_schedules_csp(ctx, locked_timetable=active_timetable)
    if not data:
        # Fallback to legacy format
        teachers_legacy = database.get_teachers_legacy_format()
        data, conflicts = scheduler.generate_schedules(teachers_legacy, locked_timetable=active_timetable)

    if not data:
        return jsonify({'error': 'Failed to generate timetable.'}), 500

    active_timetable = data

    # Count hard errors vs warnings
    hard_errors = [c for c in conflicts if c.get('severity') == 'error']
    warnings = [c for c in conflicts if c.get('severity') == 'warning']

    # Record snapshot in database
    name = f"Generated Schedule — {datetime.now().strftime('%b %d, %H:%M')}"
    database.save_timetable(name, "ALL", data, len(conflicts), is_published=0)
    database.save_timetable_version(name, "ALL", data, len(conflicts), status='Draft',
                                    change_summary='Automated CSP constraint-optimized generation')
    database.add_notification("New Timetable Proposed",
                              f"Timetable generated with {len(hard_errors)} hard errors and {len(warnings)} soft warnings.",
                              "system", "#timetables")

    return jsonify({
        'status': 'ok',
        'data': data,
        'conflicts': conflicts,
        'diagnostics': data.get('unassigned_diagnostics', []),
        'summary': {
            'total_conflicts': len(conflicts),
            'hard_errors': len(hard_errors),
            'warnings': len(warnings),
            'locked_sessions_preserved': data.get('locked_count', 0)
        }
    })

@app.route('/api/timetables/current', methods=['GET'])
def get_current_timetable():
    tt = get_current_active_timetable()
    if not tt:
        return jsonify({'error': 'No timetable available.'}), 404
    conflicts = scheduler.detect_conflicts(tt)
    return jsonify({
        'status': 'ok',
        'data': tt,
        'conflicts': conflicts
    })

@app.route('/api/timetables/validate', methods=['POST'])
def validate_timetable():
    payload = request.get_json() or {}
    tt_data = payload.get('timetable_data') or get_current_active_timetable()
    conflicts = scheduler.detect_conflicts(tt_data)
    hard_errors = [c for c in conflicts if c.get('severity') == 'error']
    return jsonify({
        'status': 'ok',
        'conflicts': conflicts,
        'hard_errors_count': len(hard_errors),
        'valid': len(hard_errors) == 0
    })

@app.route('/api/timetables/update_slot', methods=['POST'])
def update_timetable_slot():
    """Update a specific cell in the active timetable, validate, and return new state."""
    global active_timetable
    payload = request.get_json() or {}
    year = payload.get('year', '').lower()
    day_idx = payload.get('day_index')
    slot_idx = payload.get('slot_index')
    new_subject = payload.get('subject', '').strip()
    new_teacher = payload.get('teacher', '').strip()
    new_room = payload.get('room', '').strip()
    is_locked = payload.get('isLocked')

    tt = get_current_active_timetable()
    if not tt or year not in tt:
        return jsonify({'error': 'Invalid timetable or year specification.'}), 400

    if day_idx is None or slot_idx is None or day_idx >= len(tt[year]) or slot_idx >= len(tt[year][day_idx]['slots']):
        return jsonify({'error': 'Slot coordinates out of bounds.'}), 400

    target_slot = tt[year][day_idx]['slots'][slot_idx]
    if target_slot.get('isRecess'):
        return jsonify({'error': 'Cannot edit protected recess slot.'}), 400

    # Apply changes
    target_slot['subject'] = new_subject
    target_slot['teacher'] = new_teacher
    target_slot['room'] = new_room
    if is_locked is not None:
        target_slot['isLocked'] = bool(is_locked)

    if new_subject and new_teacher:
        target_slot['text'] = f"{new_subject}({new_teacher})"
    elif new_subject:
        target_slot['text'] = new_subject
    else:
        target_slot['text'] = ""

    # Re-validate
    conflicts = scheduler.detect_conflicts(tt)
    active_timetable = tt

    return jsonify({
        'status': 'ok',
        'data': tt,
        'conflicts': conflicts,
        'updated_slot': target_slot
    })

@app.route('/api/timetables/toggle_lock', methods=['POST'])
def toggle_slot_lock():
    """Toggle the locked status of a cell so it is preserved during re-generation."""
    global active_timetable
    payload = request.get_json() or {}
    year = payload.get('year', '').lower()
    day_idx = payload.get('day_index')
    slot_idx = payload.get('slot_index')
    day_name = payload.get('day')
    slot_id = payload.get('slot_id')

    tt = get_current_active_timetable()
    if not tt or year not in tt:
        return jsonify({'error': 'Invalid timetable specification.'}), 400

    target_slot = None
    if day_idx is not None and slot_idx is not None:
        if 0 <= day_idx < len(tt[year]) and 0 <= slot_idx < len(tt[year][day_idx]['slots']):
            target_slot = tt[year][day_idx]['slots'][slot_idx]
    elif day_name and slot_id is not None:
        for row in tt[year]:
            if row.get('day') == day_name:
                for s in row.get('slots', []):
                    if s.get('slot_id') == slot_id or s.get('slot_number') == slot_id:
                        target_slot = s
                        break
                break

    if not target_slot:
        return jsonify({'error': 'Slot not found.'}), 404

    if target_slot.get('isRecess'):
        return jsonify({'error': 'Recess slots are permanently locked.'}), 400

    target_slot['isLocked'] = not target_slot.get('isLocked', False)
    active_timetable = tt

    return jsonify({
        'status': 'ok',
        'isLocked': target_slot['isLocked'],
        'data': tt
    })


# ═════════════════════════════════════════════════════════
# VERSION HISTORY & APPROVAL WORKFLOW
# ═════════════════════════════════════════════════════════
@app.route('/api/timetables/versions', methods=['GET'])
def list_versions():
    year = request.args.get('year')
    versions = database.get_timetable_versions(year)
    return jsonify({'status': 'ok', 'data': versions})

@app.route('/api/timetables/versions/<int:version_id>', methods=['GET'])
def get_version(version_id):
    v = database.get_timetable_version(version_id)
    if not v:
        return jsonify({'error': 'Version not found.'}), 404
    return jsonify({'status': 'ok', 'data': v})

@app.route('/api/timetables/restore/<int:version_id>', methods=['POST'])
def restore_version(version_id):
    global active_timetable
    v = database.get_timetable_version(version_id)
    if not v or 'timetable_data' not in v:
        return jsonify({'error': 'Version record invalid or missing.'}), 404

    active_timetable = v['timetable_data']
    conflicts = scheduler.detect_conflicts(active_timetable)
    database.save_timetable_version(f"Restored from v{v['version_number']}", v['academic_year_code'], active_timetable, len(conflicts), status='Draft', change_summary=f"Restored from version {v['version_number']}")
    database.add_notification("Timetable Restored", f"Reverted active timetable to version {v['version_number']} ({v['name']}).", "system", "#versions")

    return jsonify({'status': 'ok', 'data': active_timetable, 'conflicts': conflicts})

@app.route('/api/timetables/publish/<int:version_id>', methods=['POST'])
def publish_version(version_id):
    """
    Publish an approved timetable version.
    Precondition: Prevents publication if unresolved hard conflicts remain (Requirement 10).
    """
    v = database.get_timetable_version(version_id)
    if not v or 'timetable_data' not in v:
        return jsonify({'error': 'Version not found.'}), 404

    conflicts = scheduler.detect_conflicts(v['timetable_data'])
    hard_errors = [c for c in conflicts if c.get('severity') == 'error']
    if hard_errors:
        return jsonify({
            'error': f"Cannot publish timetable: {len(hard_errors)} unresolved hard conflict(s) remain. Resolve all clashes first.",
            'hard_errors': hard_errors
        }), 400

    database.publish_timetable_version(version_id)
    database.add_notification("Official Timetable Published", f"Version {version_id} ({v['name']}) is now approved and live for students and faculty.", "publish", "#timetables")
    return jsonify({'status': 'ok', 'message': 'Timetable published successfully.'})

@app.route('/api/timetables/save', methods=['POST'])
def save_current_timetable():
    global active_timetable
    payload = request.get_json() or {}
    name = payload.get('name', f"Timetable {datetime.now().strftime('%b %d, %Y')}")
    summary = payload.get('summary', 'Manual revision saved')
    status = payload.get('status', 'Approved')

    tt = get_current_active_timetable()
    if not tt:
        return jsonify({'error': 'No active timetable to save.'}), 400

    conflicts = scheduler.detect_conflicts(tt)
    v_id, v_num = database.save_timetable_version(name, "ALL", tt, len(conflicts), status=status, change_summary=summary)
    database.save_timetable(name, "ALL", tt, len(conflicts), is_published=(1 if status == 'Published' else 0))
    database.add_notification(f"Version Saved (v{v_num})", f"{name} saved as {status}.", "system", "#versions")

    return jsonify({'status': 'ok', 'version_id': v_id, 'version_number': v_num})


# ═════════════════════════════════════════════════════════
# NOTIFICATION CENTER
# ═════════════════════════════════════════════════════════
@app.route('/api/notifications', methods=['GET'])
def list_notifications():
    unread_only = request.args.get('unread') == '1'
    notifs = database.get_notifications(limit=50, unread_only=unread_only)
    return jsonify({'status': 'ok', 'data': notifs})

@app.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
def mark_read(notif_id):
    database.mark_notification_read(notif_id)
    return jsonify({'status': 'ok'})

@app.route('/api/notifications/read_all', methods=['POST'])
def mark_all_read():
    database.mark_all_notifications_read()
    return jsonify({'status': 'ok'})


# ═════════════════════════════════════════════════════════
# MULTI-FORMAT EXPORTS (PDF, EXCEL, WORD, CSV)
# ═════════════════════════════════════════════════════════
@app.route('/api/export/<file_format>/<target_type>/<target_id>', methods=['GET'])
def export_file(file_format, target_type, target_id):
    tt = get_current_active_timetable()
    if not tt:
        return jsonify({'error': 'No timetable available to export.'}), 404

    settings = database.get_settings()
    inst_name = settings.get('institution_name', 'Slotify Institute of Technology')
    session_str = f"{settings.get('academic_session', '2026-2027')} ({settings.get('semester', 'Odd Semester')})"

    headers = ['Day'] + tt.get('timeSlots', ["9:45-10:45", "10:45-11:45", "11:45-12:45", "12:45-1:45", "1:45-2:15", "2:15-3:15", "3:15-4:15"])
    rows = []
    title = "Academic Timetable"
    subtitle = session_str
    filename_base = "timetable"

    if target_type == 'year':
        year_key = target_id.lower()
        if year_key not in tt:
            return jsonify({'error': f"Unknown year '{target_id}'."}), 400
        rows = tt[year_key]
        year_name = {'se': 'Second Year (SE)', 'te': 'Third Year (TE)', 'be': 'Final Year (BE)'}.get(year_key, year_key.upper())
        title = f"{year_name} — Class Timetable"
        filename_base = f"{year_key}_timetable"

    elif target_type == 'faculty':
        fac_data = scheduler.get_faculty_timetable(tt, target_id)
        rows = fac_data['grid']
        title = f"Individual Faculty Timetable — Prof. {target_id}"
        subtitle = f"{session_str} | Teaching Load: {fac_data['total_hours']} Hours/Week"
        filename_base = f"faculty_{target_id}_schedule"

    elif target_type == 'classroom':
        room_data = scheduler.get_classroom_timetable(tt, target_id)
        rows = room_data['grid']
        title = f"Classroom Allocation Schedule — Room {target_id}"
        subtitle = f"{session_str} | Utilization: {room_data['utilization_rate']}%"
        filename_base = f"room_{target_id}_schedule"

    else:
        return jsonify({'error': 'Invalid target type.'}), 400

    try:
        if file_format == 'pdf':
            buf = exporter.export_pdf(title, subtitle, headers, rows, institution=inst_name)
            return send_file(buf, as_attachment=True, download_name=f"{filename_base}.pdf", mimetype='application/pdf')

        elif file_format in ['excel', 'xlsx']:
            buf = exporter.export_excel(title, subtitle, headers, rows, institution=inst_name)
            return send_file(buf, as_attachment=True, download_name=f"{filename_base}.xlsx",
                             mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        elif file_format in ['docx', 'word']:
            buf = exporter.export_docx(title, subtitle, headers, rows, institution=inst_name)
            return send_file(buf, as_attachment=True, download_name=f"{filename_base}.docx",
                             mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

        elif file_format == 'csv':
            buf = exporter.export_csv(title, headers, rows)
            return send_file(buf, as_attachment=True, download_name=f"{filename_base}.csv", mimetype='text/csv')

        else:
            return jsonify({'error': f"Unsupported export format '{file_format}'."}), 400

    except Exception as e:
        return jsonify({'error': f"Export failed: {str(e)}"}), 500


# ═════════════════════════════════════════════════════════
# SETTINGS & DEMO CONTROLS (REQUIREMENT 4)
# ═════════════════════════════════════════════════════════
@app.route('/api/settings', methods=['GET'])
def get_settings():
    return jsonify({'status': 'ok', 'data': database.get_settings()})

@app.route('/api/settings', methods=['POST'])
def update_settings():
    data = request.get_json() or {}
    database.update_settings_bulk(data)
    return jsonify({'status': 'ok'})

@app.route('/api/demo/load', methods=['POST'])
def api_load_demo():
    """Button 1: Load Demo Data without overwriting user data."""
    global active_timetable
    try:
        res = database.load_demo_data()
        teachers = database.get_teachers_legacy_format()
        data, conflicts = scheduler.generate_schedules(teachers)
        active_timetable = data
        database.save_timetable("Demo Approved Schedule", "ALL", data, len(conflicts), is_published=1, is_demo=1)
        database.add_notification("Demo Data Loaded", res['message'], "system", "")
        return jsonify(res)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/demo/erase', methods=['POST'])
def api_erase_demo():
    """Button 2: Erase Demo Data strictly preserving all user-created records."""
    global active_timetable
    try:
        res = database.erase_demo_data()
        active_timetable = None
        # Try fetching remaining user timetable
        latest = database.get_latest_timetable()
        if latest and 'timetable_data' in latest:
            active_timetable = latest['timetable_data']
        database.add_notification("Demo Data Purged", res['message'], "system", "")
        return jsonify(res)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/demo/reset', methods=['POST'])
@app.route('/api/reset_sample', methods=['POST'])
def api_reset_demo():
    """Reset Demo Environment: clears demo records and reloads pristine demo dataset."""
    global active_timetable
    try:
        database.reset_to_sample_data()
        teachers = database.get_teachers_legacy_format()
        data, conflicts = scheduler.generate_schedules(teachers)
        active_timetable = data
        database.save_timetable("Demo Approved Schedule", "ALL", data, len(conflicts), is_published=1, is_demo=1)
        database.save_timetable_version("Demo Approved Schedule", "ALL", data, len(conflicts), status='Published', change_summary='Demo dataset reset', is_demo=1)
        database.add_notification("Platform Reset Complete", "Demo dataset restored successfully.", "system", "")
        return jsonify({'status': 'ok', 'message': 'Demo dataset reset successfully.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ═════════════════════════════════════════════════════════
# INTERACTIVE WORKFLOW & DEMO PRELOAD (REQUIREMENTS 2-10)
# ═════════════════════════════════════════════════════════
@app.route('/api/workflow/config', methods=['GET'])
def get_workflow_config():
    """Return complete academic configuration for 7-step wizard."""
    ctx = database.get_scheduling_context()
    settings = ctx.get('settings', {})

    config = {
        'academic_setup': {
            'college_name': settings.get('institution_name', 'Slotify Institute of Technology'),
            'department': settings.get('department_name', 'Computer Science & Engineering'),
            'academic_year': settings.get('academic_session', '2026-2027'),
            'semester': settings.get('semester', 'Odd Semester'),
            'working_days': ctx.get('working_days', ["MON", "TUE", "WED", "THU", "FRI", "SAT"]),
            'start_time': settings.get('college_start_time', '09:45'),
            'end_time': settings.get('college_end_time', '16:15'),
            'theory_duration': int(settings.get('theory_duration_mins', 60)),
            'practical_duration': int(settings.get('practical_duration_mins', 120)),
            'short_break_time': settings.get('short_break_time', '11:45'),
            'short_break_duration': int(settings.get('short_break_duration_mins', 0)),
            'lunch_break_time': settings.get('lunch_break_time', '13:45'),
            'lunch_break_duration': int(settings.get('lunch_break_duration_mins', 30)),
            'max_lectures_per_day': int(settings.get('max_lectures_per_day', 6)),
            'max_faculty_weekly_hours': int(settings.get('max_faculty_weekly_hours', 24))
        },
        'classes': ctx.get('divisions', []),
        'subjects': ctx.get('subjects', []),
        'faculty': ctx.get('teachers', []),
        'classrooms': ctx.get('classrooms', []),
        'preferences': {
            'hard_faculty_no_overlap': True,
            'hard_room_no_overlap': True,
            'hard_break_protection': True,
            'hard_capacity_enforcement': True,
            'hard_max_workload': True,
            'soft_even_distribution': True,
            'soft_slot_preference': True,
            'soft_avoid_long_gaps': True,
            'soft_no_consecutive_same_subject': True,
            'max_consecutive_lectures': 3
        }
    }
    return jsonify({'status': 'ok', 'data': config})


@app.route('/api/demo/preload', methods=['POST'])
def demo_preload():
    """Load demo dataset into database and return full workflow configuration."""
    try:
        database.load_demo_data()
        return get_workflow_config()
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/workflow/generate', methods=['POST'])
def workflow_generate():
    """Generate timetable from wizard state, running CSP algorithm."""
    global active_timetable
    payload = request.get_json() or {}

    try:
        # Save academic setup settings if provided
        if 'academic_setup' in payload:
            setup = payload['academic_setup']
            settings_update = {
                'institution_name': setup.get('college_name'),
                'department_name': setup.get('department'),
                'academic_session': setup.get('academic_year'),
                'semester': setup.get('semester'),
                'college_start_time': setup.get('start_time'),
                'college_end_time': setup.get('end_time'),
                'theory_duration_mins': str(setup.get('theory_duration', 60)),
                'practical_duration_mins': str(setup.get('practical_duration', 120)),
                'lunch_break_time': setup.get('lunch_break_time', '13:45'),
                'lunch_break_duration_mins': str(setup.get('lunch_break_duration', 30)),
                'max_lectures_per_day': str(setup.get('max_lectures_per_day', 6)),
                'max_faculty_weekly_hours': str(setup.get('max_faculty_weekly_hours', 24))
            }
            database.update_settings_bulk({k: v for k, v in settings_update.items() if v is not None})

        ctx = database.get_scheduling_context()
        if not ctx.get('teachers'):
            return jsonify({'error': 'No faculty members found. Please ensure at least one faculty member is added.'}), 400

        data, conflicts = scheduler.generate_schedules_csp(ctx, locked_timetable=active_timetable)
        if not data:
            teachers_legacy = database.get_teachers_legacy_format()
            data, conflicts = scheduler.generate_schedules(teachers_legacy, locked_timetable=active_timetable)

        if not data:
            return jsonify({'error': 'Constraint satisfaction scheduler could not find a conflict-free solution. Check classroom capacities and faculty availability.'}), 422

        active_timetable = data
        hard_errors = [c for c in conflicts if c.get('severity') == 'error']
        warnings = [c for c in conflicts if c.get('severity') == 'warning']

        total_sessions = 0
        for k in ['se', 'te', 'be']:
            if k in data and isinstance(data[k], list):
                for row in data[k]:
                    if isinstance(row, dict):
                        for s in row.get('slots', []):
                            if isinstance(s, dict) and s.get('subject') and not s.get('isRecess'):
                                total_sessions += 1

        name = f"Generated Timetable — {datetime.now().strftime('%b %d, %H:%M')}"
        database.save_timetable(name, "ALL", data, len(conflicts), is_published=0)
        database.save_timetable_version(name, "ALL", data, len(conflicts), status='Draft',
                                        change_summary='Generated from Interactive Workflow CSP Engine')
        database.add_notification("Timetable Generated", f"Schedule generated with {len(hard_errors)} hard errors.", "system", "#timetables")

        return jsonify({
            'status': 'ok',
            'data': data,
            'conflicts': conflicts,
            'diagnostics': data.get('unassigned_diagnostics', []),
            'summary': {
                'total_conflicts': len(conflicts),
                'hard_errors': len(hard_errors),
                'warnings': len(warnings),
                'locked_sessions_preserved': data.get('locked_count', 0),
                'total_sessions': total_sessions
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# ═════════════════════════════════════════════════════════
# LEGACY COMPATIBILITY ENDPOINTS
# ═════════════════════════════════════════════════════════
@app.route('/api/add_teachers', methods=['POST'])
def legacy_add_teachers():
    data = request.get_json() or {}
    t_list = data.get('teachers', [])
    imported = database.bulk_import_teachers(t_list)
    return jsonify({'status': 'ok', 'count': imported})

@app.route('/api/load_sample', methods=['GET'])
def legacy_load_sample():
    teachers = database.get_teachers_legacy_format()
    return jsonify(teachers)

@app.route('/api/download/<year>', methods=['GET'])
def legacy_download(year):
    return export_file('docx', 'year', year)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    print(f"Starting Slotify server on http://127.0.0.1:{port}")
    app.run(debug=True, host='127.0.0.1', port=port)
