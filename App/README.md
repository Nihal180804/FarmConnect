# Local Farmer Management System (Flask frontend)

## Overview
This is a Flask frontend for the Local Farmer Management System. It uses your existing MySQL database (you provided SQL dump) and calls existing stored procedures and functions where appropriate.

Files you provided:
- `config.py` — used for DB configuration. :contentReference[oaicite:4]{index=4}
- `localfarmers management.sql` — DB schema, stored procedures, triggers, demo data. Import this to your MySQL server before running the app. :contentReference[oaicite:5]{index=5}

## Setup

1. Create a Python virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate      # on Windows: venv\Scripts\activate
pip install -r requirements.txt
