# TaskFlow — Task Management Application

A responsive full-stack task manager built with Flask, SQLite, HTML, CSS, and JavaScript. Includes user authentication, per-user task privacy, task CRUD, priorities, due dates, status filters, search, and a session-authenticated JSON API.

## Features

- **Authentication:** register, sign in, sign out; passwords stored as Werkzeug password hashes.
- **Authorization:** task queries and mutations are scoped to the signed-in user's ID. Users cannot edit or delete another user's tasks by changing an ID.
- **Task CRUD:** create, view, edit, complete/reopen, and delete tasks.
- **Organization:** Pending / In Progress / Completed statuses, Low / Medium / High priority, optional due dates, search and filters.
- **Responsive UI:** mobile-friendly layout, task editor modal, empty states, confirmation before deletion, and feedback messages.
- **JSON API:** session-authenticated endpoints under `/api/tasks` for integrations and dynamic clients.
- **SQLite persistence:** database and tables are initialized automatically on startup.

## Run locally

Python 3.10+ is recommended.

```bash
# Windows PowerShell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000, create an account, and start adding tasks. On macOS/Linux, activate with `source .venv/bin/activate` instead.

Set a strong `SECRET_KEY` environment variable before deployment. The fallback key is for local development only. The SQLite database defaults to `tasks.db` beside `app.py`; set `TASKS_DATABASE` to choose another path.

## JSON API (same-origin, signed-in session required)

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/tasks` | List the signed-in user's tasks |
| POST | `/api/tasks` | Create a task; JSON body includes `title`, optional `description`, `status`, `priority`, `due_date` |
| GET | `/api/tasks/<id>` | Read one owned task |
| PUT | `/api/tasks/<id>` | Update an owned task |
| DELETE | `/api/tasks/<id>` | Delete an owned task |

Valid status values: `Pending`, `In Progress`, `Completed`. Valid priority values: `Low`, `Medium`, `High`. API endpoints use the same login session and ownership checks as the web interface.

## Deploying

For a quick demo, use a Python host that supports Flask and persistent storage. Add environment variables `SECRET_KEY` (a long random value) and, if available, `TASKS_DATABASE` pointing to persistent storage. Start command: `waitress-serve --host=0.0.0.0 --port=$PORT app:app` (adjust to your provider's required port syntax). Ensure the SQLite database is on persistent storage; an ephemeral filesystem may reset data after redeploy/restart. Follow the chosen host's current setup instructions.

## Project structure

```text
app.py                 Flask routes, authentication, database and JSON API
templates/             Jinja HTML templates
static/style.css       Responsive design and component styles
static/app.js          Modal interactions and delete confirmation
requirements.txt       Python dependencies
```

## Security notes and limitations

This is an educational project. Use HTTPS in production, set a strong secret key, and add CSRF protection/rate limiting before public production use. SQLite is suitable for a small demonstration; use a managed database for a larger multi-user deployment. No WebSocket dependency is included because real-time updates were optional in the task brief.
