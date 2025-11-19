# database_assignment4

## 1. Setup environment
### Linux/macOS users
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

### Windows users
python3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

## 2. Setup database
### Windows users, powershell (PostgreSQL 18) (example user 3530 with password 35303530)
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U 3530 -d postgres -c "CREATE DATABASE my_company_db;"
set DATABASE_URL="postgresql://3530:35303530@localhost/my_company_db"

### Linux/macOS users (example)
createdb my_company_db
export DATABASE_URL="postgresql://user:pass@localhost/my_company_db"

## 3. Load schema and your additions
### Windows users
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U 3530 -d my_company_db -f company_v3.02.sql
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U 3530 -d my_company_db -f team_setup.sql

### Linux/macOS users
psql -d $DATABASE_URL -f company_v3.02.sql
psql -d $DATABASE_URL -f team_setup.sql

## 4. Run the app
flask run