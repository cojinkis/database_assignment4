# home.py
from flask import Blueprint, url_for, g, render_template, request, Response, flash, redirect
from utilities import get_db_connection
import psycopg
import io
import csv

bp = Blueprint("home", __name__) # Blueprint lets us split program into components, with home used for the url_for('home.home') 
# __name__ tells Flask where it comes from

@bp.route("/", endpoint="home")
def home():
    """
    A2. Home – Employee Overview

    If not logged in: 
        -Show the login/register links and a db health link
        -No queries or employee table
    If logged in:
        -Run sql queries on employee name, department name, # of dependants, # of projects, and total hours
        -Filter by department, name
        -Sort by name/hours ASC/DESC
    """

    health_link = url_for("health_db")
    user = getattr(g, "user", None) # g.user is set but auth.load_lopgged_in_user and if it is None, nobody is logged in

    # Not logged in
    if user is None:

        # Links for auth blueprint routes: login and register
        login_link = url_for("auth.login")
        register_link = url_for("auth.register")

        # home.html is in the logged out portion, and we return values to guard missing keys
        return render_template(
            "home.html",
            logged_in=False,
            username=None,
            login_link=login_link,
            register_link=register_link,
            logout_link=None,
            health_link=health_link,
            employees=[],
            departments=[],
            current_dept="",
            q="",
            sort_by="name",
            order="asc",
        )

    # Logged-in user: User is not None
    try:
        username = user["username"]
    except (TypeError, KeyError):
        # fallback if user is a tuple
        username = user[1]

    # URL to logout
    logout_link = url_for("auth.logout")

    dept = request.args.get("dept", type=int)                  # Convert to an Int. Not an Int or missing = None
    q = (request.args.get("q") or "").strip()                  # User input for the name search box
    sort_by = request.args.get("sort_by", "name")              # Sort by name or total hours, otherwise just name
    order = (request.args.get("order") or "asc").lower()       # order by name or total hours, set all to lowercase

    # Error handling
    if order not in ("asc", "desc"):
        order = "asc"

    # Can't let user input determine the search --> Whitelist OrderBy
    if sort_by == "total_hours":
        sort_expr = f"total_hours {order.upper()}, e.lname ASC, e.fname ASC" # Sort by hours then last name then first name
    else:
        
        sort_by = "name" # default: sort by name
        sort_expr = f"e.lname {order.upper()}, e.fname {order.upper()}, e.minit {order.upper()}" # Sort by last name, then first name, then minit

    # Build the WHERE clause
    where_clauses = []
    params = []

    # user picked department in hte dropdown
    if dept is not None:
        where_clauses.append("e.dno = %s")
        params.append(dept)

    # user typed something in the search box
    if q:
        where_clauses.append(
            "LOWER(e.fname || ' ' || COALESCE(e.minit, '') || ' ' || e.lname) LIKE %s"
        )
        params.append(f"%{q.lower()}%")

    # join clauses if applicable
    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    # corresponds to main A2 requirements
    sql = f"""
        SELECT
            e.ssn,
            e.fname,
            e.minit,
            e.lname,
            d.dname AS department_name,
            COALESCE(COUNT(DISTINCT dep.dependent_name), 0) AS num_dependents,
            COALESCE(COUNT(DISTINCT w.pno), 0)              AS num_projects,
            COALESCE(SUM(w.hours), 0)                       AS total_hours
        FROM employee e
        LEFT JOIN department d ON e.dno = d.dnumber
        LEFT JOIN dependent dep ON e.ssn = dep.essn
        LEFT JOIN works_on w   ON e.ssn = w.essn
        {where_sql}
        GROUP BY e.ssn, e.fname, e.minit, e.lname, d.dname
        ORDER BY {sort_expr}
    """

    employees = []
    departments = []

    conn = get_db_connection()
    try:
        # Use dict_row for nicer access in template
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            # Employee overview
            cur.execute(sql, params)
            employees = cur.fetchall()

            # Department list for dropdown
            cur.execute(
                "SELECT dnumber, dname FROM department ORDER BY dname"
            )
            departments = cur.fetchall()
    finally:
        conn.close()

    return render_template(
        "home.html",
        logged_in=True,
        username=username,
        login_link=None,
        register_link=None,
        logout_link=logout_link,
        health_link=health_link,
        employees=employees,
        departments=departments,
        current_dept=str(dept) if dept is not None else "",
        q=q,
        sort_by=sort_by,
        order=order,
    )


@bp.route("/export")
def export_home_data():
    """
    Exports the current filtered and sorted employee overview as a CSV file.
    This function re-uses the exact same query logic from the home() view.
    """
    user = getattr(g, "user", None)
    if user is None:
        flash("You must be logged in to export data.")
        return redirect(url_for("auth.login"))

    # Re-use all filter and sort logic from the home() function
    dept = request.args.get("dept", type=int)
    q = (request.args.get("q") or "").strip()
    sort_by = request.args.get("sort_by", "name")
    order = (request.args.get("order") or "asc").lower()

    if order not in ("asc", "desc"):
        order = "asc"

    if sort_by == "total_hours":
        sort_expr = f"total_hours {order.upper()}, e.lname ASC, e.fname ASC"
    else:
        sort_by = "name"
        sort_expr = f"e.lname {order.upper()}, e.fname {order.upper()}, e.minit {order.upper()}"

    where_clauses = []
    params = []
    if dept is not None:
        where_clauses.append("e.dno = %s")
        params.append(dept)
    if q:
        where_clauses.append(
            "LOWER(e.fname || ' ' || COALESCE(e.minit, '') || ' ' || e.lname) LIKE %s"
        )
        params.append(f"%{q.lower()}%")

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    sql = f"""
        SELECT
            e.fname, e.minit, e.lname,
            d.dname AS department_name,
            COALESCE(COUNT(DISTINCT dep.dependent_name), 0) AS num_dependents,
            COALESCE(COUNT(DISTINCT w.pno), 0) AS num_projects,
            COALESCE(SUM(w.hours), 0) AS total_hours
        FROM employee e
        LEFT JOIN department d ON e.dno = d.dnumber
        LEFT JOIN dependent dep ON e.ssn = dep.essn
        LEFT JOIN works_on w ON e.ssn = w.essn
        {where_sql}
        GROUP BY e.ssn, e.fname, e.minit, e.lname, d.dname
        ORDER BY {sort_expr}
    """

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    finally:
        conn.close()

    # Build CSV in memory using the csv module
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Full Name', 'Department', 'Dependents', 'Projects', 'Total Hours'])
    for r in rows:
        full_name = f"{r[0]} {r[1] or ''} {r[2]}".replace('  ', ' ').strip()
        writer.writerow([full_name, r[3], r[4], r[5], float(r[6])])

    csv_data = output.getvalue()
    output.close()

    headers = {'Content-Type': 'text/csv', 'Content-Disposition': 'attachment; filename="employee_overview.csv"'}
    return Response(csv_data, headers=headers)