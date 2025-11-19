from flask import Flask, jsonify, url_for
import os
import auth, home
from utilities import get_db_connection
try:
    import psycopg
except Exception:
    psycopg = None

app = Flask(__name__)
app.config.from_mapping(
    SECRET_KEY='dev',
)
app.register_blueprint(auth.bp)
app.register_blueprint(home.bp)





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
