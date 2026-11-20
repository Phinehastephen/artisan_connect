# Backend application

This folder contains the Django REST API and its domain applications. The React
client is maintained in the separate
`Phinehastephen/artisan_connect_frontend` repository.

Run management commands from the repository root so Django loads the root
`.env` file:

```powershell
python backend/manage.py runserver
python backend/manage.py migrate
python backend/manage.py test
```

Install the backend dependencies from the repository root with:

```powershell
pip install -r backend/requirements.txt
```

Copy `.env.example` to the repository root as `.env`, then configure PostgreSQL
and `CORS_ALLOWED_ORIGINS`. The default CORS origins allow the local Vite
development servers at `http://localhost:5173` and `http://127.0.0.1:5173`.
See the repository-level README for architecture and local development
instructions.
