from flask import Flask, jsonify, url_for
import os
from . import auth

try:
    import psycopg
except Exception:
    psycopg = None

app = Flask(__name__)
app.register_blueprint(auth.bp)

def get_db_connection():
    """Return a new psycopg connection using the DATABASE_URL env var.

    Raises ValueError if psycopg is not installed or DATABASE_URL is not set.
    """
    if psycopg is None:
        raise ValueError("psycopg is not installed; install requirements.txt")
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    # If the env var was set with surrounding quotes (common on Windows cmd: set VAR="value"),
    # strip surrounding single or double quotes so it actually works.
    database_url = database_url.strip()
    database_url = database_url.strip('"\'')
    return psycopg.connect(database_url)


@app.route("/")
def home():
    link = url_for('health_db')
    return f"hello world. Check DB health at <a href='{link}'> {link} </a>"


@app.route('/health-db')
def health_db():
    """A simple route that checks the database connection and runs a test query.

    Tries to run `SELECT COUNT(*) FROM employee` and returns the result. If that
    table doesn't exist, it falls back to `SELECT 1` to verify connectivity.
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            try:
                # try a complex query first, assuming employee table exists
                cur.execute('SELECT COUNT(*) FROM employee')
                cnt = cur.fetchone()[0]
                return jsonify(status='ok', message='connected', employee_count=cnt)
            except Exception:
                # fallback to a simple query to verify connection, ignoring table absence
                cur.execute('SELECT 1')
                _ = cur.fetchone()[0]
                return jsonify(status='ok', message='connected (no employee table)')
    except Exception as e:
        return jsonify(status='error', message=str(e)), 500


if __name__ == "__main__":
    app.run(debug=True)
