# Cinderwell

Cinderwell is a double-entry ledger for one operator's own company. It keeps a chart of accounts, posted journals, invoices, bills, monthly budgets, a profit and loss, and a balance sheet.

The person who owns the books is the only user. Customer and vendor names are labels on that owner's documents. The repository does not ship with anyone's real financial records.

## Stack

- Backend: Django 5, Django REST Framework, SimpleJWT, django-filter, drf-spectacular. SQLite by default, PostgreSQL when `DATABASE_URL` is a postgres URL. The Postgres driver is psycopg 3, installed from PyPI, not copied into this tree.
- Frontend: React 18, TypeScript, Vite, React Router, TanStack Query, TanStack Table, Zustand, Axios, React Hook Form, Zod, Recharts, date-fns, Lucide, and clsx.

## Layout

- `backend/` Django API
- `frontend/` React client
- `PLAN.md` posting rules and the work still ahead

## Run locally

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Frontend, in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and create a ledger. Copy `backend/.env.example` to `backend/.env` if you want to override the secret key or point at PostgreSQL.

## License

Released under the [MIT License](LICENSE).
