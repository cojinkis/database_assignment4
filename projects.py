from flask import Blueprint
import os
from utilities import get_db_connection
from flask import render_template, request, redirect, url_for, flash, g, Response
import csv
import io

bp = Blueprint('projects', __name__, url_prefix='/projects')

@bp.before_request
def require_login():
    # Protect all routes in this blueprint: only authenticated users may access
    if g.get('user') is None:
        return redirect(url_for('auth.login'))

@bp.route('/')
def list_projects():
    """List all projects."""
    # Whitelist sorting options — map allowed keys to fixed column names
    sort_by = request.args.get('sort_by', type=str)
    order = request.args.get('order', 'asc').lower()
    if order not in ('asc', 'desc'):
        order = 'asc'

    ALLOWED_SORT = {
        'headcount': 'headcount',
        'total_hours': 'total_hours',
    }
    sort_col = ALLOWED_SORT.get(sort_by)

    # Main SQL query to get project details
    # We use CASE WHEN to handle NULLs for headcount and total_hours
    sql = (
        "SELECT p.Pnumber AS pnumber, p.Pname AS project_name, d.Dname AS department_name, "                # project info
        "CASE WHEN COUNT(DISTINCT w.Essn) IS NULL THEN 0 ELSE COUNT(DISTINCT w.Essn) END AS headcount, "    # headcount
        "CASE WHEN SUM(w.Hours) IS NULL THEN 0 ELSE SUM(w.Hours) END AS total_hours "                       # total hours
        "FROM Project p "                                                                                   # from Project
        "LEFT JOIN Department d ON p.Dnum = d.Dnumber "                                                     # join Department
        "LEFT JOIN Works_On w ON p.Pnumber = w.Pno "                                                        # join Works_On    
        "GROUP BY p.Pnumber, p.Pname, d.Dname"                                                              # group by project and department    
    )
    # Append ORDER BY if a whitelisted sort column was provided
    if sort_col:
        sql = sql + f" ORDER BY {sort_col} {order}"

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            # rows are tuples; map to dicts for template
            projects = []
            for r in rows:
                projects.append({
                    'pnumber': r[0],
                    'project_name': r[1],
                    'department_name': r[2],
                    'headcount': int(r[3]) if r[3] is not None else 0,
                    'total_hours': float(r[4]) if r[4] is not None else 0.0,
                })
    finally:
        conn.close()

    return render_template('projects.html', projects=projects)

@bp.route('/export')
def export_projects():
    """Export the current filtered/sorted projects list as CSV."""
    # Reuse same sorting whitelist logic
    sort_by = request.args.get('sort_by', type=str)
    order = request.args.get('order', 'asc').lower()
    if order not in ('asc', 'desc'):
        order = 'asc'

    ALLOWED_SORT = {
        'headcount': 'headcount',
        'total_hours': 'total_hours',
    }
    sort_col = ALLOWED_SORT.get(sort_by)

    sql = (
        "SELECT p.Pnumber AS pnumber, p.Pname AS project_name, d.Dname AS department_name, "
        "COALESCE(COUNT(DISTINCT w.Essn),0) AS headcount, COALESCE(SUM(w.Hours),0) AS total_hours "
        "FROM Project p "
        "LEFT JOIN Department d ON p.Dnum = d.Dnumber "
        "LEFT JOIN Works_On w ON p.Pnumber = w.Pno "
        "GROUP BY p.Pnumber, p.Pname, d.Dname"
    )
    if sort_col:
        sql = sql + f" ORDER BY {sort_col} {order}"

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    finally:
        conn.close()

    # Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Pnumber', 'Project Name', 'Department', 'Headcount', 'Total Hours'])
    for r in rows:
        writer.writerow([r[0], r[1], r[2] or '', int(r[3] or 0), float(r[4] or 0.0)])

    csv_data = output.getvalue()
    output.close()

    headers = {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename="projects_export.csv"'
    }
    return Response(csv_data, headers=headers)

@bp.route('/<int:project_id>', methods=('GET','POST'))
def project_detail(project_id):
    """Show details for a specific project."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Verify project exists and get project name
            cur.execute("SELECT Pname FROM Project WHERE Pnumber = %s", (project_id,))
            proj = cur.fetchone()
            if proj is None:
                return render_template('project_detail.html', error='Project not found', project_id=project_id), 404
            project_name = proj[0]

            # Handle form submission (Upsert)
            if request.method == 'POST':
                # Enforce admin-only for modifications
                if g.get('user') is None or g.get('user').get('role') != 'admin':
                    flash('You do not have permission to modify project assignments.')
                    return redirect(url_for('.project_detail', project_id=project_id))
                emp_ssn = request.form.get('employee_ssn')
                hours = request.form.get('hours')
                try:
                    hours_val = float(hours)
                    if hours_val < 0:
                        raise ValueError('Hours must be non-negative')
                except Exception as e:
                    flash(f'Invalid hours value: {e}')
                    return redirect(url_for('.project_detail', project_id=project_id))

                if not emp_ssn:
                    flash('Please select an employee')
                    return redirect(url_for('.project_detail', project_id=project_id))

                # Perform atomic upsert: add hours if exists, insert if not
                upsert_sql = (
                    "INSERT INTO Works_On (Essn, Pno, Hours) VALUES (%s, %s, %s) "
                    "ON CONFLICT (Essn, Pno) DO UPDATE SET Hours = Works_On.Hours + EXCLUDED.Hours"
                )
                cur.execute(upsert_sql, (emp_ssn, project_id, hours_val))
                conn.commit()
                flash('Assignment updated')
                return redirect(url_for('.project_detail', project_id=project_id))

            # GET: fetch assigned employees
            cur.execute(
                "SELECT e.Ssn, e.Fname, e.Minit, e.Lname, w.Hours "
                "FROM Works_On w JOIN Employee e ON w.Essn = e.Ssn "
                "WHERE w.Pno = %s ORDER BY e.Lname, e.Fname",
                (project_id,)
            )
            assigned = cur.fetchall()

            # Fetch all employees for dropdown
            cur.execute("SELECT Ssn, Fname, Minit, Lname FROM Employee ORDER BY Lname, Fname")
            all_emps = cur.fetchall()

    finally:
        conn.close()

    # Map rows into dicts for template convenience, formatting names
    assigned_list = [
        {'ssn': r[0], 'full_name': f"{r[1]} {r[2]} {r[3]}".replace('  ', ' '), 'hours': float(r[4])}
        for r in assigned
    ]
    employees = [
        {'ssn': r[0], 'full_name': f"{r[1]} {r[2]} {r[3]}".replace('  ', ' ')}
        for r in all_emps
    ]

    return render_template('project_detail.html', project_id=project_id, project_name=project_name,
                           assigned=assigned_list, employees=employees)
