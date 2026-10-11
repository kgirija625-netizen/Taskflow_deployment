# Project Report: TaskFlow Task Management Application

## 1. Introduction
TaskFlow is a responsive web application for organizing personal tasks. It lets a user create an account, sign in, add tasks, set priorities and due dates, change task status, search/filter the task list, and update or remove tasks.

## 2. Problem Statement
To-do lists scattered across notes and messages can make it difficult to prioritize work and track completion. The application provides a single interface with persistent task storage and visible progress.

## 3. Objectives
- Implement registration and login with password hashing.
- Restrict each user to their own tasks.
- Provide create, read, update, and delete operations.
- Support status, priority, due date, search, and filtering.
- Build a responsive interface for desktop and mobile.
- Provide JSON API endpoints for basic integrations.

## 4. Technology Stack
- **Python + Flask:** server-side routing, request handling, sessions, and validation.
- **SQLite:** relational persistence for users and tasks without a separate database server.
- **Werkzeug security:** password hashing and verification.
- **HTML/Jinja:** reusable page templates and server-rendered content.
- **CSS:** responsive layout and visual components.
- **JavaScript:** task modal, edit-form population, and delete confirmation.
- **JSON API:** structured responses for integration with clients.

## 5. System Design
A browser sends a request to Flask. Flask checks the session, validates input, and queries SQLite. Task database operations always include the authenticated user's ID. The server returns HTML pages or JSON API responses.

```text
Browser / Mobile UI
        |
        v
Flask routes and session authentication
        |
        +---- Input validation / ownership checks
        |
        v
SQLite database (users, tasks)
        |
        v
HTML response or JSON API response
```

## 6. Database Design
- **users:** `id`, `name`, unique `email`, `password_hash`, `created_at`.
- **tasks:** `id`, `user_id`, `title`, `description`, `status`, `priority`, `due_date`, `created_at`, `updated_at`.
- `tasks.user_id` references `users.id` with cascading deletion; an index supports filtering by user and status.

## 7. Functional Modules
1. **Authentication:** registration, sign-in, sign-out; password hashes are stored instead of plaintext passwords.
2. **Task creation:** title and optional description, priority, status, and due date.
3. **Task listing:** search by title/description and filter by status.
4. **Task editing:** update task information and timestamp.
5. **Completion and deletion:** toggle task completion or delete after confirmation.
6. **JSON API:** list/create and read/update/delete tasks using the current authenticated session.
7. **Responsive UI:** adaptive layout for desktop and mobile screens.

## 8. Validation and Authorization
Required fields and allowed status/priority values are checked on the server. SQL queries use parameterized statements. Task reads, edits, and deletes include both task ID and authenticated user ID; a user cannot access another account's task simply by guessing its ID.

## 9. Testing Checklist
- Register with a new email and verify that the dashboard opens.
- Try duplicate registration and an invalid password length.
- Sign out and sign back in with correct/incorrect credentials.
- Create, edit, complete, reopen, search, filter, and delete tasks.
- Create two user accounts and verify that each account sees only its own tasks.
- Check responsive layout at a narrow mobile viewport.
- While signed in, check `GET /api/tasks` and test JSON create/update/delete requests.

## 10. Limitations and Future Enhancements
Real-time WebSockets are not included because they were optional. Further improvements could add CSRF protection, password reset, email verification, team sharing, notifications, automated tests, and a managed production database.

## 11. Conclusion
TaskFlow demonstrates a full-stack application with authentication, database persistence, CRUD workflows, responsive presentation, and a basic JSON API. The project emphasizes per-user authorization and clear task organization.
