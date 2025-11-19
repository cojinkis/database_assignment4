from flask import Blueprint
import os
from utilities import get_db_connection
from flask import render_template, request

bp = Blueprint('managers', __name__, url_prefix='/managers')

@bp.route('/')
def list_managers():
    ''' corresponds to A6 requirement '''

    # SQL commands

    # gets the number of employees in each department
    num_emp = (
        'SELECT Dname,COUNT(SSN) AS NoOfEmployees ' 
        'FROM Employee, Department ' 
        'WHERE Dnumber=Dno ' 
        'GROUP BY Dname ' 
    )

    display = []
    display_dict = {
        "dept_info": "",
        "manager_name": "",
        "emp_count": None,
        "dept_tot_hours": None
    }

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            l =cur.execute(num_emp)
            for entry in l:
                thingy_squared = str(entry[0]) + ", " + str(entry[1])

                placeholder = display_dict.copy()
                placeholder['dept_info'] = thingy_squared
                display.append(placeholder)

            # num_emp_rows = cur.fetchall()
            # print(num_emp_rows)
            # for r in num_emp_rows:
            #     print(r)
            #     entry = display_dict.copy()
            #     entry['dept_info'] = r[] + ", " + str(r['NoOfEmployees'])
            #     display.append(entry)
    finally:
        conn.close()

    return render_template('managers.html', display=display)
