
from functools import wraps

import mysql.connector
from mysql.connector import Error
from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Replace this with a long, random secret key.
app.secret_key = "2642005"


def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="hadeer@2642005",
        database="registration"
    )


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("todos"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please fill in all fields.")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must be at least 8 characters.")
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)

        connection = None
        cursor = None

        try:
            connection = get_db_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (%s, %s, %s)
                """,
                (name, email, password_hash)
            )
            connection.commit()

            flash("Account created successfully. Please log in.")
            return redirect(url_for("login"))

        except Error as error:
            if connection and connection.is_connected():
                connection.rollback()

            if getattr(error, "errno", None) == 1062:
                flash("This email is already registered.")
            else:
                app.logger.error("Registration database error: %s", error)
                flash("Could not create your account. Please try again.")

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    return render_template("register.html")


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
                SELECT user_id, name, password_hash
                FROM users
                WHERE email = %s
                """,
                (email,)
            )
            user = cursor.fetchone()

            if user and check_password_hash(
                user["password_hash"], password
            ):
                session.clear()
                session["user_id"] = user["user_id"]
                session["name"] = user["name"]
                return redirect(url_for("todos"))

            flash("Invalid email or password.")

        except Error as error:
            app.logger.error("Login database error: %s", error)
            flash("Could not log in. Please try again.")

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    return render_template("login.html")


@app.route("/todos")
@login_required
def todos():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT todo_id, title, is_done
            FROM todos
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (session["user_id"],)
        )
        user_todos = cursor.fetchall()

        return render_template(
            "todos.html",
            todos=user_todos,
            name=session["name"]
        )

    except Error as error:
        app.logger.error("Loading tasks failed: %s", error)
        flash("Could not load your tasks.")
        return redirect(url_for("login"))

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@app.route("/todos/add", methods=["POST"])
@login_required
def add_todo():
    title = request.form.get("title", "").strip()

    if not title:
        flash("Task title cannot be empty.")
        return redirect(url_for("todos"))

    if len(title) > 200:
        flash("Task title must be 200 characters or fewer.")
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
        flash("Task added successfully.")

    except Error as error:
        if connection and connection.is_connected():
            connection.rollback()
        app.logger.error("Adding task failed: %s", error)
        flash("Could not add the task.")

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

    return redirect(url_for("todos"))


@app.route("/todos/<int:todo_id>/complete", methods=["POST"])
@login_required
def complete_todo(todo_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE todos
            SET is_done = 1
            WHERE todo_id = %s AND user_id = %s
            """,
            (todo_id, session["user_id"])
        )
        connection.commit()

        if cursor.rowcount:
            flash("Task marked as completed.")
        else:
            flash("Task not found.")

    except Error as error:
        if connection and connection.is_connected():
            connection.rollback()
        app.logger.error("Completing task failed: %s", error)
        flash("Could not update the task.")

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

    return redirect(url_for("todos"))


@app.route("/todos/<int:todo_id>/delete", methods=["POST"])
@login_required
def delete_todo(todo_id):
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
            flash("Task deleted successfully.")
        else:
            flash("Task not found.")

    except Error as error:
        if connection and connection.is_connected():
            connection.rollback()
        app.logger.error("Deleting task failed: %s", error)
        flash("Could not delete the task.")

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

    return redirect(url_for("todos"))


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)