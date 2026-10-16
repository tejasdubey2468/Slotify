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

app = Flask(__name__)
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
            teachers = database.get_teachers_legacy_format()
            if teachers:
                data, conflicts = scheduler.generate_schedules(teachers)
                active_timetable = data
                database.save_timetable("Initial Approved Schedule", "ALL", data, len(conflicts), is_published=1)
                database.save_timetable_version("Initial Approved Schedule", "ALL", data, len(conflicts), status='Published', change_summary='Initial auto-generation on platform startup')
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

@app.route('/api/academic_years', methods=['GET'])
def list_academic_years():
    return jsonify({'status': 'ok', 'data': database.get_academic_years()})

@app.route('/api/divisions', methods=['GET'])
def list_divisions():
    return jsonify({'status': 'ok', 'data': database.get_divisions()})


# ═════════════════════════════════════════════════════════
# SUBJECTS MANAGEMENT
# ═════════════════════════════════════════════════════════
@app.route('/api/subjects', methods=['GET'])
def list_subjects():
    subjects = database.get_subjects()
    year_filter = request.args.get('year')
    if year_filter:
        subjects = [s for s in subjects if s.get('year_code') == year_filter]
    return jsonify({'status': 'ok', 'data': subjects})

@app.route('/api/subjects', methods=['POST'])
def create_subject():
    data = request.get_json() or {}
    if not data.get('name') or not data.get('code'):
        return jsonify({'error': 'Subject name and code are required.'}), 400
    new_id = database.add_subject(data)
    database.add_notification(f"Subject Added: {data['code']}", f"New subject '{data['name']}' added to curriculum.", "system", "#subjects")
    return jsonify({'status': 'ok', 'id': new_id})

@app.route('/api/subjects/<int:sub_id>', methods=['PUT'])
def update_subject(sub_id):
    data = request.get_json() or {}
    database.update_subject(sub_id, data)
    return jsonify({'status': 'ok'})

@app.route('/api/subjects/<int:sub_id>', methods=['DELETE'])
def delete_subject(sub_id):
    database.delete_subject(sub_id)
    return jsonify({'status': 'ok'})


# ═════════════════════════════════════════════════════════
# CLASSROOMS & LABORATORIES
# ═════════════════════════════════════════════════════════
@app.route('/api/classrooms', methods=['GET'])
def list_classrooms():
    return jsonify({'status': 'ok', 'data': database.get_classrooms()})

@app.route('/api/classrooms', methods=['POST'])
def create_classroom():
    data = request.get_json() or {}
    if not data.get('name') or not data.get('room_number'):
        return jsonify({'error': 'Room name and number are required.'}), 400
    new_id = database.add_classroom(data)
    return jsonify({'status': 'ok', 'id': new_id})

@app.route('/api/classrooms/<int:room_id>', methods=['PUT'])
def update_classroom(room_id):
    data = request.get_json() or {}
    database.update_classroom(room_id, data)
    return jsonify({'status': 'ok'})

@app.route('/api/classrooms/<int:room_id>', methods=['DELETE'])
def delete_classroom(room_id):
    database.delete_classroom(room_id)
    return jsonify({'status': 'ok'})

@app.route('/api/classroom/<room_number>/timetable', methods=['GET'])
def get_classroom_timetable(room_number):
    tt = get_current_active_timetable()
    if not tt:
        return jsonify({'error': 'No active timetable found.'}), 404
    data = scheduler.get_classroom_timetable(tt, room_number)
    return jsonify({'status': 'ok', 'data': data})


# ═════════════════════════════════════════════════════════
# TEACHERS & FACULTY
# ═════════════════════════════════════════════════════════
@app.route('/api/teachers', methods=['GET'])
def list_teachers():
    return jsonify({'status': 'ok', 'data': database.get_teachers()})

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
    new_id = database.add_teacher(data)
    database.add_notification(f"Faculty Onboarded: {data['name']}", f"Initial profile created for {data['name']} ({data['initials']}).", "system", "#faculty")
    return jsonify({'status': 'ok', 'id': new_id})

@app.route('/api/teachers/<int:teacher_id>', methods=['PUT'])
def update_teacher(teacher_id):
    data = request.get_json() or {}
    database.update_teacher(teacher_id, data)
    return jsonify({'status': 'ok'})

@app.route('/api/teachers/<int:teacher_id>', methods=['DELETE'])
def delete_teacher(teacher_id):
    database.delete_teacher(teacher_id)
    return jsonify({'status': 'ok'})


# ═════════════════════════════════════════════════════════
# FACULTY DIRECTORY & INDIVIDUAL TIMETABLES
# ═════════════════════════════════════════════════════════
@app.route('/api/faculty/timetables', methods=['GET'])
def get_all_faculty_timetables():
    """Return all faculty profiles paired with their assigned workload and schedule overview."""
    teachers = database.get_teachers()
    tt = get_current_active_timetable()
    result = []
    for t in teachers:
        summary = scheduler.get_faculty_timetable(tt, t['initials']) if tt else {'total_hours': 0, 'years': [], 'subjects': [], 'rooms': []}
        result.append({
            'id': t['id'],
            'name': t['name'],
            'initials': t['initials'],
            'designation': t['designation'],
            'email': t['email'],
            'time_slot': t['time_slot'],
            'max_hours_per_week': t['max_hours_per_week'],
            'scheduled_hours': summary.get('total_hours', 0),
            'years': summary.get('years', []),
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
# TIME SLOTS & RECESS MANAGEMENT
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
    new_id = database.add_holiday(data)
    database.add_notification(f"Holiday Added: {data['name']}", f"Official holiday scheduled for {data['date']}.", "holiday", "#calendar")
    return jsonify({'status': 'ok', 'id': new_id})

@app.route('/api/holidays/<int:holiday_id>', methods=['DELETE'])
def delete_holiday(holiday_id):
    database.delete_holiday(holiday_id)
    return jsonify({'status': 'ok'})


# ═════════════════════════════════════════════════════════
# TIMETABLE GENERATION & CONFLICT DETECTION
# ═════════════════════════════════════════════════════════
@app.route('/api/generate', methods=['POST'])
def generate_timetable():
    """Run full constraint-solving generation across SE, TE, and BE."""
    global active_timetable
    teachers = database.get_teachers_legacy_format()
    if not teachers:
        return jsonify({'error': 'No faculty records found. Please ensure faculty are added.'}), 400

    data, conflicts = scheduler.generate_schedules(teachers)
    if not data:
        return jsonify({'error': 'Failed to generate timetable.'}), 500

    active_timetable = data

    # Record snapshot in database
    name = f"Generated Schedule — {datetime.now().strftime('%b %d, %H:%M')}"
    database.save_timetable(name, "ALL", data, len(conflicts), is_published=0)
    database.save_timetable_version(name, "ALL", data, len(conflicts), status='Draft', change_summary='Automatic constraint-optimized generation')
    database.add_notification("New Timetable Proposed", f"Timetable generated with {len(conflicts)} detected conflicts. Pending approval.", "system", "#timetables")

    return jsonify({
        'status': 'ok',
        'data': data,
        'conflicts': conflicts,
        'summary': {
            'total_conflicts': len(conflicts),
            'hard_errors': len([c for c in conflicts if c.get('severity') == 'error']),
            'warnings': len([c for c in conflicts if c.get('severity') == 'warning']),
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
    return jsonify({
        'status': 'ok',
        'conflicts': conflicts,
        'valid': len([c for c in conflicts if c.get('severity') == 'error']) == 0
    })

@app.route('/api/timetables/update_slot', methods=['POST'])
def update_timetable_slot():
    """Update a specific cell in the active timetable and revalidate."""
    global active_timetable
    payload = request.get_json() or {}
    year = payload.get('year', '').lower()
    day_idx = payload.get('day_index')
    slot_idx = payload.get('slot_index')
    new_subject = payload.get('subject', '').strip()
    new_teacher = payload.get('teacher', '').strip()
    new_room = payload.get('room', '').strip()

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
    # Save a record of the restoration event
    database.save_timetable_version(f"Restored from v{v['version_number']}", v['academic_year_code'], active_timetable, len(conflicts), status='Draft', change_summary=f"Restored from version {v['version_number']}")
    database.add_notification("Timetable Restored", f"Reverted active timetable to version {v['version_number']} ({v['name']}).", "system", "#versions")

    return jsonify({'status': 'ok', 'data': active_timetable, 'conflicts': conflicts})

@app.route('/api/timetables/publish/<int:version_id>', methods=['POST'])
def publish_version(version_id):
    database.publish_timetable_version(version_id)
    database.add_notification("Official Timetable Published", f"Version {version_id} is now approved and live for students and faculty.", "publish", "#timetables")
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
    """
    Unified multi-format export route.
    file_format: pdf | excel | docx | csv
    target_type: year (se/te/be) | faculty (initials) | classroom (room_num)
    """
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

    # Dispatch to appropriate exporter
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
# SETTINGS & SAMPLE DATA
# ═════════════════════════════════════════════════════════
@app.route('/api/settings', methods=['GET'])
def get_settings():
    return jsonify({'status': 'ok', 'data': database.get_settings()})

@app.route('/api/settings', methods=['POST'])
def update_settings():
    data = request.get_json() or {}
    for k, v in data.items():
        database.update_setting(k, v)
    return jsonify({'status': 'ok'})

@app.route('/api/reset_sample', methods=['POST'])
def reset_sample():
    global active_timetable
    database.reset_to_sample_data()
    teachers = database.get_teachers_legacy_format()
    data, conflicts = scheduler.generate_schedules(teachers)
    active_timetable = data
    database.save_timetable("Demo Approved Schedule", "ALL", data, len(conflicts), is_published=1)
    database.save_timetable_version("Demo Approved Schedule", "ALL", data, len(conflicts), status='Published', change_summary='Pristine demo database reset')
    database.add_notification("Platform Reset Complete", "Database restored to standard demo dataset with 16 faculty and zero conflicts.", "system", "")
    return jsonify({'status': 'ok', 'message': 'Demo database restored successfully.'})


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
    port = int(os.environ.get('PORT', 5000))
    try:
        app.run(debug=True, port=port)
    except OSError:
        port = 5001
        print(f"Port 5000 in use. Running Slotify on http://127.0.0.1:{port}")
        app.run(debug=True, port=port)
