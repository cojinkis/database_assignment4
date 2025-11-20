from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from utilities import get_db_connection
import psycopg
import logging

# Module logger for server-side error logging. 
logger = logging.getLogger(__name__)

# Blueprint registration: all employee routes are mounted under /employees
bp = Blueprint('employees', __name__, url_prefix='/employees')


@bp.before_request
def require_login():
    """Ensure the user is authenticated before serving any employee page."""
    if g.get('user') is None:
        # If not logged in, redirect to the app's login page. We use the auth
        # blueprint's `login` endpoint name here.
        return redirect(url_for('auth.login'))

@bp.before_request
def require_admin_role():
    """Ensure the user has admin role before accessing employee management pages."""
    if g.get('user') is None or g.get('user').get('role') != "admin":
        flash('You do not have permission to access the Employees section.')
        return redirect(url_for('home.home'))

@bp.route('/')
def list_employees():
    """Return the employees list page."""
    conn = get_db_connection()
    rows = []
    try:
        with conn.cursor() as cur:
            # Select commonly displayed fields and order by last name, first name.
            cur.execute(
                "SELECT Ssn, Fname, Minit, Lname, Address, Sex, Salary, Super_ssn, Dno"
                " FROM Employee ORDER BY Lname, Fname"
            )
            rows = cur.fetchall()
    except Exception as e:
        # Log the full exception server-side for debugging and show a
        # user-friendly message in the UI.
        logger.exception('Error fetching employee list')
        flash('An error occurred while loading employees. Please try again later.')
    finally:
        conn.close()

    # Map SQL row tuples to dictionaries. Makes things easier to work with in templates.
    # The full_name field normalizes missing middle initials.
    employees = [
        {
            'ssn': r[0],
            'full_name': f"{r[1]} {r[2]} {r[3]}".replace('  ', ' '),
            'address': r[4],
            'sex': r[5],
            'salary': r[6],
            'super_ssn': r[7],
            'dno': r[8]
        }
        for r in rows
    ]

    # Render the list template. Template will handle role-based UI (e.g.
    # showing Add/Delete buttons to admins only) by inspecting `g.user`.
    return render_template('employees.html', employees=employees)


@bp.route('/add', methods=('GET', 'POST'))
def add_employee():
    """Handle adding a new employee."""

    if request.method == 'POST':
        # Pull fields from the form; use sensible defaults for optional fields.
        ssn = request.form.get('ssn')
        # The form can supply either separate name fields (`fname`, `minit`,
        # `lname`) or a single `full_name` input. 
        # We will handel both since I am not sure how I want the UI to be yet.
        fname = request.form.get('fname')
        minit = request.form.get('minit') or ''
        lname = request.form.get('lname')
        full_name = request.form.get('full_name')
        address = request.form.get('address') or ''
        sex = request.form.get('sex') or 'M'
        salary = request.form.get('salary') or 0
        super_ssn = request.form.get('super_ssn') or None
        dno = request.form.get('dno')
        bdate = request.form.get('bdate') or None
        empdate = request.form.get('empdate') or None

        # Basic required-field validation before touching the DB
        # Validate required fields and provide field-specific error messages
        missing = []
        if not ssn:
            missing.append('SSN')
        # Allow either separate first/last name fields OR a single full_name.
        if not ((fname and lname) or full_name):
            missing.append('First name and Last name (or provide Full Name)')
        if not dno:
            missing.append('Department (Dno)')

        if missing:
            flash('Missing required field(s): ' + ', '.join(missing))
            return redirect(url_for('.add_employee'))

        # If the form provided a single `full_name`, parse it into fname,
        # minit and lname. 
        # first token is first name, last token is last name, any single middle token is
        # treated as middle initial (first character). If parsing fails we
        # surface a clear error to the user.
        if not (fname and lname) and full_name:
            parts = full_name.strip().split()
            if len(parts) < 2:
                flash('Full Name must include at least first and last name.')
                return redirect(url_for('.add_employee'))
            fname = parts[0]
            lname = parts[-1]
            if len(parts) == 3:
                # Use the middle token as middle initial (single char preferred)
                mid = parts[1]
                minit = mid[0] if mid else ''
            else:
                # If there are more than 3 tokens, just take the second token
                # as the middle initial (best-effort).
                minit = parts[1][0] if len(parts) > 2 and parts[1] else ''

        # Validate numeric fields with clear error messages so users know what to fix
        try:
            if salary != 0 and salary != '0':
                salary = float(salary)
        except ValueError:
            flash('Salary must be a number (e.g. 45000 or 45000.00).')
            return redirect(url_for('.add_employee'))

        try:
            dno = int(dno)
        except (TypeError, ValueError):
            flash('Department number (Dno) must be an integer.')
            return redirect(url_for('.add_employee'))

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        "INSERT INTO Employee (Fname, Minit, Lname, Ssn, Address, Sex, Salary, Super_ssn, Dno, BDate, EmpDate) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (fname, minit, lname, ssn, address, sex, salary, super_ssn, dno, bdate, empdate)
                    )
                    conn.commit()
                    flash('Employee added')
                    return redirect(url_for('.list_employees'))
                except Exception as e:
                    # Log the full exception server-side for diagnostics.
                    logger.exception('Error inserting new employee')
                    # Database error handling
                    # show friendlier, actionable messages to the user.
                    msg = str(e)
                    sqlstate = getattr(e, 'sqlstate', None)
                    if sqlstate == '23505':
                        # unique violation (SSN already exists)
                        flash('SSN already exists. Choose a different SSN.')
                    elif sqlstate == '23503':
                        # foreign key violation: department or supervisor not found
                        flash('Foreign key error: check that Department (Dno) and Supervisor SSN exist.')
                    elif sqlstate == '22P02':
                        # invalid_text_representation (e.g. converting a string to int)
                        flash('Invalid input format: check numeric/date fields.')
                    else:
                        # Fallback to a generic message while avoiding raw DB text
                        flash('An error occurred while adding the employee. Please check your input and try again.')
                    return redirect(url_for('.add_employee'))
        finally:
            conn.close()

    # GET: render an empty form for creating a new employee. The template uses
    # `employee is None` to decide whether to show the Add form.
    return render_template('employee_form.html', action='Add', employee=None)


@bp.route('/<ssn>/edit', methods=('GET', 'POST'))
def edit_employee(ssn):
    """Edit an existing employee.

    GET: fetch the employee row and pre-fill the form.
    POST: update the editable fields (Address, Salary, Dno). Only users with
    `role == 'admin'` are allowed to perform the POST.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Fetch the existing employee record by primary key (Ssn)
            cur.execute(
                "SELECT Ssn, Fname, Minit, Lname, Address, Sex, Salary, Super_ssn, Dno"
                " FROM Employee WHERE Ssn = %s",
                (ssn,)
            )
            row = cur.fetchone()
            if row is None:
                # If the requested SSN does not exist, return a 404 response.
                return "Employee not found", 404

            if request.method == 'POST':
                # Server-side RBAC: ensure only admins may modify employee data.
                if g.get('user') is None or g.get('user').get('role') != 'admin':
                    flash('You do not have permission to edit employees.')
                    return redirect(url_for('.list_employees'))

                # Pull only the editable fields from the submitted form
                address = request.form.get('address') or ''
                salary = request.form.get('salary') or 0
                dno = request.form.get('dno')
                try:
                    cur.execute(
                        "UPDATE Employee SET Address = %s, Salary = %s, Dno = %s WHERE Ssn = %s",
                        (address, salary, dno, ssn)
                    )
                    conn.commit()
                    flash('Employee updated')
                    return redirect(url_for('.list_employees'))
                except Exception as e:
                    # Log full exception details and show a friendly message.
                    logger.exception('Error updating employee %s', ssn)
                    flash('An error occurred while updating the employee. Please try again.')
                    return redirect(url_for('.edit_employee', ssn=ssn))

            # Build a dictionary representing the employee to pass to the
            # template. The form will render fields in a read-only or editable
            # manner depending on whether it's Add vs Edit.
            # Include `full_name` so the edit form can render a single
            # read-only Full Name input (keeps UI consistent with the list page).
            employee = {
                'ssn': row[0],
                'fname': row[1],
                'minit': row[2],
                'lname': row[3],
                'full_name': f"{row[1]} {row[2] or ''} {row[3]}".replace('  ', ' '),
                'address': row[4],
                'sex': row[5],
                'salary': row[6],
                'super_ssn': row[7],
                'dno': row[8]
            }
    finally:
        conn.close()

    return render_template('employee_form.html', action='Edit', employee=employee)


@bp.route('/<ssn>/delete', methods=('POST',))
def delete_employee(ssn):
    """Delete an employee (admin only)."""
    # Enforce admin-only deletion at the server side.
    if g.get('user') is None or g.get('user').get('role') != 'admin':
        flash('You do not have permission to delete employees.')
        return redirect(url_for('.list_employees'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            try:
                # Safe, parameterized DELETE.
                cur.execute('DELETE FROM Employee WHERE Ssn = %s', (ssn,))
                conn.commit()
                flash('Employee deleted')
            except Exception as e:
                # Log details and give a friendly error message on delete
                logger.exception('Error deleting employee %s', ssn)
                # Try to detect a PostgreSQL foreign-key constraint error to
                # provide a clearer message to the user.
                sqlstate = getattr(e, 'sqlstate', None)
                if sqlstate == '23503':
                    # 23503 == foreign_key_violation
                    flash('Cannot delete employee: They are still assigned to projects, have dependents listed, or are a manager/supervisor.')
                else:
                    flash('An error occurred while deleting the employee. Please try again.')
    finally:
        conn.close()

    return redirect(url_for('.list_employees'))
