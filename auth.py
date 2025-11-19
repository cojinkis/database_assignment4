from flask import Blueprint, request, render_template, flash, redirect, url_for, session, g, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import os
from utilities import get_db_connection
import home
import psycopg


bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form.get('role')
        print(role)
        error = None

        if not username:
            error = 'Username is Required.'
        elif not password:
            error = "Password is Required"

        if error is None:
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO app_user (username, password_hash, role) VALUES (%s, %s, %s)",
                        (username, generate_password_hash(password), role)
                    )
                conn.commit() # Commit on the connection
            except conn.IntegrityError as e:
                error = f"Username is already taken."
            except Exception as e:
                error = str(e)
                flash(error)

            else:
                flash("Registration successful! Please log in.")
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template('auth/register.html')

@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        error = None
        try:
            conn = get_db_connection()
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute('SELECT * FROM app_user WHERE username = %s', (username,))
                user = cur.fetchone()

        except Exception as e:
            error = str(e)
            user = None

        if user is None:
            error = "Incorrect username or the user is not registered with the system."
        elif not check_password_hash(user['password_hash'], password):
            error = "Incorrect password."

        if error is None:
            print("login success")
            # Login successful
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for("home.home"))

        flash(error)
    return render_template('auth/login.html')

# Following function makes sure we get the user_id for the logged in user at every request in the application
@bp.before_app_request
def load_logged_in_user():
    curr_user_id = session.get('user_id')
    if curr_user_id is None:
        g.user = None
    else:
        conn = get_db_connection()
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute('SELECT * FROM app_user WHERE id = %s', (curr_user_id,))
            g.user = cur.fetchone()

@bp.route('/logout', methods=('GET', 'POST'))
def logout():
    session.clear()
    return redirect(url_for('home.home'))