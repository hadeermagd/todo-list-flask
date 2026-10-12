
import os
import bcrypt
import mysql.connector

from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)
from werkzeug.security import check_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key")


# =========================
# Database Connection
# =========================

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("MYSQL_PASSWORD", ""),
        database="registration"
    )


# =========================
# Password Helpers
# =========================

def verify_password(password, stored_hash):
    """
    Supports both:
    1. New bcrypt password hashes
    2. Older Werkzeug password hashes
    """

    if not stored_hash:
        return False, False

    # Check bcrypt hashes
    if stored_hash.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            valid = bcrypt.checkpw(
                password.encode("utf-8"),
                stored_hash.encode("utf-8")
            )
            return valid, False
        except (ValueError, TypeError):
            return False, False

    # Check legacy Werkzeug hashes
    try:
        valid = check_password_hash(stored_hash, password)
        return valid, valid
    except (ValueError, TypeError):
        return False, False


def hash_password(password):
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


# =========================
# Home Page
# =========================

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("todos"))

    return redirect(url_for("login"))


# =========================
# Register
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please fill in all fields.", "error")
            return render_template("register.html")

        password_hash = hash_password(password)
        connection = None
        cursor = None

        try:
            connection = get_db_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO users (email, name, password_hash)
                VALUES (%s, %s, %s)
                """,
                (email, name, password_hash)
            )

            connection.commit()

            flash("Account created successfully. Please log in.", "success")
            return redirect(url_for("login"))

        except mysql.connector.IntegrityError:
            flash("This email is already registered.", "error")

        except mysql.connector.Error as error:
            app.logger.error("Registration database error: %s", error)
            flash("A database error occurred. Please try again.", "error")

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    return render_template("register.html")


# =========================
# Login
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        connection = None
        cursor = None

        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT user_id, email, name, password_hash
                FROM users
                WHERE email = %s
                """,
                (email,)
            )

            user = cursor.fetchone()

            if user:
                valid, needs_upgrade = verify_password(
                    password,
                    user["password_hash"]
                )

                if valid:
                    # Upgrade an old Werkzeug hash to bcrypt
                    if needs_upgrade:
                        new_hash = hash_password(password)

                        cursor.execute(
                            """
                            UPDATE users
                            SET password_hash = %s
                            WHERE user_id = %s
                            """,
                            (new_hash, user["user_id"])
                        )
                        connection.commit()

                    session.clear()
                    session["user_id"] = user["user_id"]
                    session["email"] = user["email"]
                    session["name"] = user["name"]

                    return redirect(url_for("todos"))

            flash("Invalid email or password", "error")

        except mysql.connector.Error as error:
            app.logger.error("Login database error: %s", error)
            flash("A database error occurred. Please try again.", "error")

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    return render_template("login.html")


# =========================
# To-Do List
# =========================

@app.route("/todos")
def todos():
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT todo_id, title, is_done, created_at
            FROM todos
            WHERE user_id = %s
            ORDER BY todo_id DESC
            """,
            (session["user_id"],)
        )

        todo_list = cursor.fetchall()

        return render_template(
            "todos.html",
            todos=todo_list,
            name=session.get("name", "")
        )

    except mysql.connector.Error as error:
        app.logger.error("Loading tasks error: %s", error)
        flash("Could not load your tasks.", "error")
        return render_template(
            "todos.html",
            todos=[],
            name=session.get("name", "")
        )

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# =========================
# Add Task
# =========================

@app.route("/todos/add", methods=["POST"])
def add_todo():
    if "user_id" not in session:
        return redirect(url_for("login"))

    title = request.form.get("title", "").strip()

    if not title:
        flash("Task title cannot be empty.", "error")
        return redirect(url_for("todos"))

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO todos (user_id, title)
            VALUES (%s, %s)
            """,
            (session["user_id"], title)
        )

        connection.commit()
        flash("Task added successfully.", "success")

    except mysql.connector.Error as error:
        app.logger.error("Adding task error: %s", error)
        flash("Could not add the task.", "error")

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

    return redirect(url_for("todos"))


# =========================
# Edit Task
# =========================

@app.route("/todos/<int:todo_id>/edit", methods=["POST"])
def edit_todo(todo_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    title = request.form.get("title", "").strip()

    if not title:
        flash("Task title cannot be empty.", "error")
        return redirect(url_for("todos"))

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE todos
            SET title = %s
            WHERE todo_id = %s AND user_id = %s
            """,
            (title, todo_id, session["user_id"])
        )

        connection.commit()

        if cursor.rowcount:
            flash("Task updated successfully.", "success")
        else:
            flash("Task not found.", "error")

    except mysql.connector.Error as error:
        app.logger.error("Editing task error: %s", error)
        flash("Could not update the task.", "error")

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

    return redirect(url_for("todos"))


# =========================
# Toggle Task Status
# =========================

@app.route("/todos/<int:todo_id>/toggle", methods=["POST"])
def toggle_todo(todo_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE todos
            SET is_done = NOT is_done
            WHERE todo_id = %s AND user_id = %s
            """,
            (todo_id, session["user_id"])
        )

        connection.commit()

        if cursor.rowcount:
            flash("Task status updated successfully.", "success")
        else:
            flash("Task not found.", "error")

    except mysql.connector.Error as error:
        app.logger.error("Updating task status error: %s", error)
        flash("Could not update task status.", "error")

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

    return redirect(url_for("todos"))


# =========================
# Delete Task
# =========================

@app.route("/todos/<int:todo_id>/delete", methods=["POST"])
def delete_todo(todo_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM todos
            WHERE todo_id = %s AND user_id = %s
            """,
            (todo_id, session["user_id"])
        )

        connection.commit()

        if cursor.rowcount:
            flash("Task deleted successfully.", "success")
        else:
            flash("Task not found.", "error")

    except mysql.connector.Error as error:
        app.logger.error("Deleting task error: %s", error)
        flash("Could not delete the task.", "error")

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

    return redirect(url_for("todos"))


# =========================
# Logout
# =========================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# =========================
# Run Application
# =========================

if __name__ == "__main__":
    app.run(debug=True)