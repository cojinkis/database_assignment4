# database_assignment4

## 1. Setup environment
### Linux/macOS users
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows users
```
python3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Setup database
### Windows users

PowerShell (PostgreSQL 18) (example user `3530` with password `35303530`):

```
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U 3530 -d postgres -c "CREATE DATABASE my_company_db;"
$env:DATABASE_URL = 'postgresql://3530:35303530@localhost/my_company_db'
```

Command Prompt / `cmd.exe` (do NOT include wrapping quotes around the value):

```
"""IMPORTANT: In cmd.exe DO NOT use surrounding quotes. Use this exact form: """
set DATABASE_URL=postgresql://3530:35303530@localhost/my_company_db
```

### Linux/macOS users (example)
```
createdb my_company_db
export DATABASE_URL="postgresql://user:pass@localhost/my_company_db"
```

## 3. Load schema and your additions
### Windows users

PowerShell:

```
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U 3530 -d my_company_db -f company_v3.02.sql
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U 3530 -d my_company_db -f team_setup.sql
```

Command Prompt / `cmd.exe` (if `psql` is on PATH):

```
psql -U 3530 -d my_company_db -f company_v3.02.sql
psql -U 3530 -d my_company_db -f team_setup.sql
```

### Linux/macOS users
psql -d $DATABASE_URL -f company_v3.02.sql
psql -d $DATABASE_URL -f team_setup.sql

## 4. Run the app

Activate the virtual environment and run the Flask app directly. Make sure `DATABASE_URL` is set first (see section 2).

Windows (cmd):

```
.venv\Scripts\activate
flask run
```

Windows (PowerShell):

```
.venv\Scripts\Activate.ps1
flask run
```

Linux/macOS:

```
source .venv/bin/activate
flask run
```

The app will listen on `http://127.0.0.1:5000` by default.

## 5. Test DB route

Use the `/health-db` endpoint to verify the app can connect to the database and run a simple query.

Open in a browser: `http://127.0.0.1:5000/health-db`

Or from the command line (Windows cmd / PowerShell / Linux/macOS):

```
curl http://127.0.0.1:5000/health-db
```

The endpoint returns JSON with `status: ok` when connected, or `status: error` and an error message if the connection fails.