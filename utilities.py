import os
try:
    import psycopg
except Exception:
    psycopg = None

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