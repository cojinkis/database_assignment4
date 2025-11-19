# home.py
from flask import Blueprint, url_for, g

bp = Blueprint("home", __name__)

@bp.route("/", endpoint="home")
def index():
    """
    Landing page.
    If not logged in: show links to login/register.
    If logged in: greet user and show DB health link + logout.
    """
    health_link = url_for("health_db")

    user = getattr(g, "user", None)

    if user is not None:
        # user may be a dict (if you use dict_row) or a tuple (default psycopg)
        try:
            username = user["username"]
        except (TypeError, KeyError):
            # fallback if it's a tuple: adjust index if needed
            username = user[1]

        logout_link = url_for("auth.logout")
        return (
            f"Hello, {username}! "
            f"Check DB health at <a href='{health_link}'>{health_link}</a> | "
            f"<a href='{logout_link}'>Logout</a>"
        )

    login_link = url_for("auth.login")
    register_link = url_for("auth.register")

    return (
        f"Welcome! "
        f"<a href='{login_link}'>Login</a> or "
        f"<a href='{register_link}'>Register</a>. "
        f"Check DB health at <a href='{health_link}'>{health_link}</a>"
    )
