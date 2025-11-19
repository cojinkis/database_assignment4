from flask import Blueprint, request, render_template, flash, redirect, url_for, session, g
from werkzeug.security import generate_password_hash, check_password_hash
import os

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db() # for getting the user db, implemented later
        error = None
        if not username:
            error = 'Username is Required.'
        elif not password:
            error = "Password is Required"

        if error is None:
            try:
                db.execute(
                    "INSERT INTO app_user (username, password_hash) VALUES (?, ?)",
                    (username, generate_password_hash(password))
                )
                db.commit()
            except db.IntegrityError:
                error = f"user {username} is already registered with the system"
            else:
                return redirect(url_for("auth.login"))
            
            flash(error)
    return render_template('auth/register.html')

@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db() # for getting the user db, implemented later
        error = None
        user = db.execute(
            'SELECT * FROM app_user WHERE username = ?', (username)
        ).fetchone()

        if user is None:
            error = "Incorrect username or the user is not registered with the system"
        elif not check_password_hash(user['password_hash'], password):
            error = "Incorrect password"
        
        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('home'))
        flash(error)
    return render_template('auth/login.html')

# Following function makes sure we get the user_id for the logged in user at every request in the application
@bp.before_app_request
def load_logged_in_user():
    curr_user_id = session.get('user_id')
    if curr_user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM app_user WHERE id = ?', (curr_user_id)
        ).fetchone()

@bp.route('/logout', methods=('GET', 'POST'))
def logout():
    session.clear()
    return redirect(url_for('home'))