import os
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get('TASKS_DATABASE', BASE_DIR / 'tasks.db'))
app = Flask(__name__, static_folder=str(BASE_DIR / 'static'), template_folder=str(BASE_DIR / 'templates'))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-secret-before-public-deployment')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    with connect_db() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','In Progress','Completed')),
            priority TEXT NOT NULL DEFAULT 'Medium' CHECK(priority IN ('Low','Medium','High')),
            due_date TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_user_status ON tasks(user_id, status);
        ''')


@app.before_request
def prepare_request():
    init_db()
    g.user = None
    if session.get('user_id'):
        with connect_db() as db:
            g.user = db.execute('SELECT id, name, email FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if g.user is None:
            session.clear()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            flash('Please sign in to continue.', 'info')
            return redirect(url_for('login', next=request.path))
        return view(*args, **kwargs)
    return wrapped


def task_for_user(task_id):
    with connect_db() as db:
        task = db.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, g.user['id'])).fetchone()
    if task is None:
        abort(404)
    return task


def task_dict(row):
    return {key: row[key] for key in ('id','title','description','status','priority','due_date','created_at','updated_at')}


@app.route('/')
def index():
    return redirect(url_for('dashboard') if g.user else url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if g.user:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not name or not email or len(password) < 8:
            flash('Enter your name and email, and use a password with at least 8 characters.', 'error')
            return render_template('register.html')
        try:
            with connect_db() as db:
                db.execute('INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                           (name, email, generate_password_hash(password)))
                user_id = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()['id']
            session.clear()
            session['user_id'] = user_id
            flash('Account created. Welcome to TaskFlow!', 'success')
            return redirect(url_for('dashboard'))
        except sqlite3.IntegrityError:
            flash('An account with that email already exists. Please sign in.', 'error')
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        with connect_db() as db:
            user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('dashboard'))
        flash('Email or password is incorrect.', 'error')
    return render_template('login.html')


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    session.clear()
    flash('You have been signed out.', 'success')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    status = request.args.get('status', 'All')
    query = request.args.get('q', '').strip()
    allowed_statuses = {'All', 'Pending', 'In Progress', 'Completed'}
    if status not in allowed_statuses:
        status = 'All'
    sql = 'SELECT * FROM tasks WHERE user_id = ?'
    args = [g.user['id']]
    if status != 'All':
        sql += ' AND status = ?'; args.append(status)
    if query:
        sql += ' AND (title LIKE ? OR description LIKE ?)'; args.extend([f'%{query}%', f'%{query}%'])
    sql += " ORDER BY CASE priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END, CASE WHEN due_date IS NULL OR due_date = '' THEN 1 ELSE 0 END, due_date ASC, created_at DESC"
    with connect_db() as db:
        tasks = db.execute(sql, args).fetchall()
        counts = db.execute("SELECT COUNT(*) total, SUM(status='Pending') pending, SUM(status='In Progress') progress, SUM(status='Completed') completed FROM tasks WHERE user_id = ?", (g.user['id'],)).fetchone()
    today = datetime.now().date().isoformat()
    return render_template('dashboard.html', tasks=tasks, counts=counts, status=status, query=query, today=today)


@app.route('/tasks/new', methods=['POST'])
@login_required
def create_task():
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    status = request.form.get('status', 'Pending')
    priority = request.form.get('priority', 'Medium')
    due_date = request.form.get('due_date', '').strip() or None
    if not title:
        flash('Task title is required.', 'error')
    elif status not in {'Pending','In Progress','Completed'} or priority not in {'Low','Medium','High'}:
        flash('Please choose valid task status and priority.', 'error')
    else:
        with connect_db() as db:
            db.execute('INSERT INTO tasks (user_id,title,description,status,priority,due_date) VALUES (?,?,?,?,?,?)',
                       (g.user['id'], title, description, status, priority, due_date))
        flash('Task added successfully.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/tasks/<int:task_id>/edit', methods=['POST'])
@login_required
def edit_task(task_id):
    task_for_user(task_id)
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    status = request.form.get('status', 'Pending')
    priority = request.form.get('priority', 'Medium')
    due_date = request.form.get('due_date', '').strip() or None
    if not title or status not in {'Pending','In Progress','Completed'} or priority not in {'Low','Medium','High'}:
        flash('Check the title, status, and priority values.', 'error')
    else:
        with connect_db() as db:
            db.execute('UPDATE tasks SET title=?, description=?, status=?, priority=?, due_date=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?',
                       (title, description, status, priority, due_date, task_id, g.user['id']))
        flash('Task updated.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/tasks/<int:task_id>/toggle', methods=['POST'])
@login_required
def toggle_task(task_id):
    task = task_for_user(task_id)
    next_status = 'Completed' if task['status'] != 'Completed' else 'Pending'
    with connect_db() as db:
        db.execute('UPDATE tasks SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?',
                   (next_status, task_id, g.user['id']))
    flash('Task marked ' + next_status.lower() + '.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    task_for_user(task_id)
    with connect_db() as db:
        db.execute('DELETE FROM tasks WHERE id=? AND user_id=?', (task_id, g.user['id']))
    flash('Task deleted.', 'success')
    return redirect(url_for('dashboard'))


# Small session-authenticated JSON API for integrations and dynamic clients.
@app.route('/api/tasks', methods=['GET', 'POST'])
@login_required
def api_tasks():
    if request.method == 'GET':
        with connect_db() as db:
            rows = db.execute('SELECT * FROM tasks WHERE user_id=? ORDER BY created_at DESC', (g.user['id'],)).fetchall()
        return jsonify([task_dict(row) for row in rows])
    payload = request.get_json(silent=True) or {}
    title = str(payload.get('title', '')).strip()
    status = payload.get('status', 'Pending')
    priority = payload.get('priority', 'Medium')
    if not title or status not in {'Pending','In Progress','Completed'} or priority not in {'Low','Medium','High'}:
        return jsonify({'error': 'A title and valid status/priority are required'}), 400
    with connect_db() as db:
        cur = db.execute('INSERT INTO tasks (user_id,title,description,status,priority,due_date) VALUES (?,?,?,?,?,?)',
                         (g.user['id'], title, str(payload.get('description','')).strip(), status, priority, payload.get('due_date') or None))
        row = db.execute('SELECT * FROM tasks WHERE id=? AND user_id=?', (cur.lastrowid, g.user['id'])).fetchone()
    return jsonify(task_dict(row)), 201


@app.route('/api/tasks/<int:task_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_task_detail(task_id):
    task = task_for_user(task_id)
    if request.method == 'GET':
        return jsonify(task_dict(task))
    if request.method == 'DELETE':
        with connect_db() as db:
            db.execute('DELETE FROM tasks WHERE id=? AND user_id=?', (task_id, g.user['id']))
        return jsonify({'deleted': True, 'id': task_id})
    payload = request.get_json(silent=True) or {}
    title = str(payload.get('title', task['title'])).strip()
    description = str(payload.get('description', task['description'])).strip()
    status = payload.get('status', task['status'])
    priority = payload.get('priority', task['priority'])
    due_date = payload.get('due_date', task['due_date']) or None
    if not title or status not in {'Pending','In Progress','Completed'} or priority not in {'Low','Medium','High'}:
        return jsonify({'error': 'Invalid title, status, or priority'}), 400
    with connect_db() as db:
        db.execute('UPDATE tasks SET title=?,description=?,status=?,priority=?,due_date=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?',
                   (title, description, status, priority, due_date, task_id, g.user['id']))
        row = db.execute('SELECT * FROM tasks WHERE id=? AND user_id=?', (task_id, g.user['id'])).fetchone()
    return jsonify(task_dict(row))


@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Task not found'}), 404
    return render_template('404.html'), 404


if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
