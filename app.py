
import os
import re
import sqlite3
import csv
import io
from datetime import datetime

from flask import Flask, request, jsonify, session, render_template, Response
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

DATABASE = "tasks.db"

PRIORITIES = ("low", "medium", "high")
STATUSES = ("pending", "done")
CATEGORIES = ("work", "study", "personal")


# DATABASE CONNECTION
def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


# DATABASE MIGRATION
def ensure_category_column():
    db = get_db()

    columns = [
        row["name"]
        for row in db.execute("PRAGMA table_info(tasks)").fetchall()
    ]

    if "category" not in columns:
        db.execute("""
            ALTER TABLE tasks
            ADD COLUMN category TEXT NOT NULL DEFAULT 'work'
        """)
        db.commit()

    db.close()


# CURRENT USER
def current_user():
    return session.get("user_id")


# DATE VALIDATION
def valid_date(value):
    if value in (None, ""):
        return True

    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


# HOME
@app.route("/")
def home():
    return render_template("index.html")


# REGISTER
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json() or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if not re.fullmatch(r"[A-Za-z0-9_]{3,30}", username):
        return jsonify(error="Username must contain 3-30 letters, numbers or underscore"), 400

    if len(password) < 6:
        return jsonify(error="Password must be at least 6 characters"), 400

    db = get_db()

    try:
        db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password))
        )
        db.commit()

    except sqlite3.IntegrityError:
        return jsonify(error="Username already exists"), 409

    finally:
        db.close()

    return jsonify(message="Registered successfully"), 201


# LOGIN
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json() or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    db = get_db()

    user = db.execute(
        "SELECT id, password_hash FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    db.close()

    if user and check_password_hash(user["password_hash"], password):
        session["user_id"] = user["id"]
        return jsonify(message="Login successful")

    return jsonify(error="Invalid username or password"), 401


# LOGOUT
@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify(message="Logged out successfully")


# DASHBOARD
@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    uid = current_user()

    if not uid:
        return jsonify(error="Login required"), 401

    today = datetime.now().date().isoformat()
    db = get_db()

    stats = db.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) AS done,
            SUM(
                CASE
                    WHEN status = 'pending'
                    AND due_date IS NOT NULL
                    AND due_date < ?
                    THEN 1 ELSE 0
                END
            ) AS overdue
        FROM tasks
        WHERE user_id = ?
    """, (today, uid)).fetchone()

    db.close()

    total = stats["total"] or 0
    pending = stats["pending"] or 0
    done = stats["done"] or 0
    overdue = stats["overdue"] or 0

    progress = round((done / total) * 100) if total else 0

    return jsonify({
        "total": total,
        "pending": pending,
        "done": done,
        "overdue": overdue,
        "progress": progress
    })


# GET TASKS
@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    uid = current_user()

    if not uid:
        return jsonify(error="Login required"), 401

    status = request.args.get("status", "all")
    search = request.args.get("q", "").strip()

    sql = """
        SELECT id, title, status, priority, due_date, category
        FROM tasks
        WHERE user_id = ?
    """

    params = [uid]

    if status in STATUSES:
        sql += " AND status = ?"
        params.append(status)

    if search:
        sql += " AND title LIKE ?"
        params.append("%" + search + "%")

    sql += """
        ORDER BY status = 'done',
        CASE priority
            WHEN 'high' THEN 0
            WHEN 'medium' THEN 1
            ELSE 2
        END,
        due_date IS NULL, due_date, id DESC
    """

    db = get_db()
    rows = db.execute(sql, params).fetchall()
    db.close()

    return jsonify([dict(row) for row in rows])


# ADD TASK
@app.route("/api/tasks", methods=["POST"])
def add_task():
    uid = current_user()

    if not uid:
        return jsonify(error="Login required"), 401

    data = request.get_json() or {}

    title = str(data.get("title", "")).strip()
    priority = data.get("priority", "medium")
    category = data.get("category", "work")
    due_date = data.get("due_date") or None

    if not title or len(title) > 200:
        return jsonify(error="Title required (maximum 200 characters)"), 400

    if priority not in PRIORITIES:
        return jsonify(error="Invalid priority"), 400

    if category not in CATEGORIES:
        return jsonify(error="Invalid category"), 400

    if not valid_date(due_date):
        return jsonify(error="Invalid due date"), 400

    db = get_db()

    cursor = db.execute("""
        INSERT INTO tasks
        (user_id, title, priority, due_date, category)
        VALUES (?, ?, ?, ?, ?)
    """, (uid, title, priority, due_date, category))

    db.commit()
    task_id = cursor.lastrowid
    db.close()

    return jsonify({
        "id": task_id,
        "title": title,
        "status": "pending",
        "priority": priority,
        "due_date": due_date,
        "category": category
    }), 201


# UPDATE TASK
@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    uid = current_user()

    if not uid:
        return jsonify(error="Login required"), 401

    data = request.get_json() or {}

    fields = []
    params = []

    if "title" in data:
        title = str(data["title"]).strip()

        if not title or len(title) > 200:
            return jsonify(error="Invalid title"), 400

        fields.append("title = ?")
        params.append(title)

    if "status" in data:
        if data["status"] not in STATUSES:
            return jsonify(error="Invalid status"), 400

        fields.append("status = ?")
        params.append(data["status"])

    if "priority" in data:
        if data["priority"] not in PRIORITIES:
            return jsonify(error="Invalid priority"), 400

        fields.append("priority = ?")
        params.append(data["priority"])

    if "category" in data:
        if data["category"] not in CATEGORIES:
            return jsonify(error="Invalid category"), 400

        fields.append("category = ?")
        params.append(data["category"])

    if "due_date" in data:
        if not valid_date(data["due_date"]):
            return jsonify(error="Invalid due date"), 400

        fields.append("due_date = ?")
        params.append(data["due_date"] or None)

    if not fields:
        return jsonify(error="Nothing to update"), 400

    params.extend([task_id, uid])

    db = get_db()

    cursor = db.execute(
        "UPDATE tasks SET " + ", ".join(fields) +
        " WHERE id = ? AND user_id = ?",
        params
    )

    db.commit()
    changed = cursor.rowcount
    db.close()

    if not changed:
        return jsonify(error="Task not found"), 404

    return jsonify(message="Task updated successfully")


# DELETE TASK
@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    uid = current_user()

    if not uid:
        return jsonify(error="Login required"), 401

    db = get_db()

    cursor = db.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, uid)
    )

    db.commit()
    changed = cursor.rowcount
    db.close()

    if not changed:
        return jsonify(error="Task not found"), 404

    return jsonify(message="Task deleted successfully")


@app.route("/api/tasks/export", methods=["GET"])
def export_tasks():
    if "user_id" not in session:
        return jsonify({"error": "Please login first"}), 401

    conn = get_db()

    try:
        tasks = conn.execute("""
            SELECT title, category, priority, status, due_date
            FROM tasks
            WHERE user_id = ?
            ORDER BY id DESC
        """, (session["user_id"],)).fetchall()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Task Title", "Category", "Priority", "Status", "Due Date"
        ])

        for task in tasks:
            writer.writerow([
                task["title"],
                task["category"],
                task["priority"],
                task["status"],
                task["due_date"] or ""
            ])

        return Response(
            "\ufeff" + output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition":
                "attachment; filename=taskflow_tasks.csv"
            }
        )
    finally:
        conn.close()

# RUN APPLICATION
if __name__ == "__main__":
    # DATABASE INITIALIZATION AND MIGRATION
def ensure_category_column():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            priority TEXT NOT NULL DEFAULT 'medium',
            due_date TEXT,
            category TEXT NOT NULL DEFAULT 'work',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    columns = [
        row["name"]
        for row in db.execute("PRAGMA table_info(tasks)").fetchall()
    ]

    if "category" not in columns:
        db.execute("""
            ALTER TABLE tasks
            ADD COLUMN category TEXT NOT NULL DEFAULT 'work'
        """)

    db.commit()
    db.close()