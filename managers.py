from flask import Blueprint
import os
from utilities import get_db_connection
from flask import render_template, request

bp = Blueprint('managers', __name__, url_prefix='/managers')

@bp.route('/')
def list_managers():
    ''' Lists the manager's summary '''

    # SQL query to get all I need in one step
    # Coalesce used to return NULL if no value associated
    sql = (
        "SELECT "
        "CONCAT(d.Dname, ' (', d.Dnumber, ')') AS dept_name_num, "
        "COALESCE(NULLIF(CONCAT_WS(' ', m.Fname, m.Minit, m.Lname), ''), 'None') AS manager_name, "
        "COUNT(DISTINCT e.Ssn) AS employee_count, "
        "COALESCE(SUM(w.Hours), 0) AS total_hours "
        "FROM Department d "
        "LEFT JOIN Employee m ON d.Mgr_ssn = m.Ssn "
        "LEFT JOIN Employee e ON d.Dnumber = e.Dno "
        "LEFT JOIN Works_On w ON e.Ssn = w.Essn "
        "GROUP BY d.Dnumber, d.Dname, m.Fname, m.Minit, m.Lname "
        "ORDER BY d.Dname"
    )

    display = []
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            for r in rows:
                display.append({
                    "dept_name_num": r[0],
                    "manager_name": r[1],
                    "emp_count": r[2],
                    "total_hours": float(r[3])
                })
    finally:
        conn.close()

    return render_template('managers.html', display=display)
