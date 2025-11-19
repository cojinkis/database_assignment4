from flask import Blueprint
import os
from utilities import get_db_connection
from flask import render_template, request

bp = Blueprint('projects', __name__, url_prefix='/projects')

@bp.route('/')
def list_projects():
    """List all projects."""
    # Whitelist sorting options
    sort_by = request.args.get('sort_by', type=str)
    order = request.args.get('order', 'asc').lower()
    if order not in ('asc', 'desc'):
        order = 'asc'

    sort_expr = None
    if sort_by == 'headcount':
        sort_expr = f"headcount {order}"
    elif sort_by == 'total_hours':
        sort_expr = f"total_hours {order}"

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
    if sort_expr:
        sql = sql + f" ORDER BY {sort_expr}"

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
