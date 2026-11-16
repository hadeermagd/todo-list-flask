
import os
import uuid
from pathlib import Path
from functools import wraps

import bcrypt
import mysql.connector
from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from werkzeug.utils import secure_filename


# --------------------------------------------------
# Application configuration
# --------------------------------------------------

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

IMAGE_FOLDER = Path(app.root_path) / "static" / "images"
IMAGE_FOLDER.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


# --------------------------------------------------
# Database connection
# --------------------------------------------------

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "registration")
    )


# --------------------------------------------------
# Authentication helpers
# --------------------------------------------------

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


def hash_password(password):
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(stored_password, entered_password):
    if not stored_password:
        return False

    try:
        if stored_password.startswith(("$2a$", "$2b$", "$2y$")):
            return bcrypt.checkpw(
                entered_password.encode("utf-8"),
                stored_password.encode("utf-8")
            )

        # Support passwords hashed by the previous application.
        return check_password_hash(stored_password, entered_password)

    except (ValueError, TypeError):
        return False


def get_current_user():
    user_id = session.get("user_id")

    if user_id is None:
        return None

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT user_id, name, email FROM users WHERE user_id = %s",
            (user_id,)
        )
        return cursor.fetchone()

    finally:
        cursor.close()
        connection.close()


# --------------------------------------------------
# Image helpers
# --------------------------------------------------

def save_image(upload):
    if not upload or not upload.filename:
        return None

    filename = secure_filename(upload.filename)

    if "." not in filename:
        raise ValueError("Invalid image filename.")

    extension = filename.rsplit(".", 1)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Allowed formats: PNG, JPG, JPEG, WEBP.")

    unique_name = f"{uuid.uuid4().hex}.{extension}"
    upload.save(IMAGE_FOLDER / unique_name)

    return unique_name


def delete_image(filename):
    if not filename:
        return

    # Only delete files inside static/images.
    safe_name = Path(filename).name

    if safe_name != filename:
        return

    image_path = IMAGE_FOLDER / safe_name

    if image_path.is_file():
        image_path.unlink()


# --------------------------------------------------
# Home
# --------------------------------------------------

@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("todos"))

    return redirect(url_for("login"))


# --------------------------------------------------
# Registration
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("todos"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or len(name) > 100:
            flash("Enter a name of up to 100 characters.", "error")
            return render_template("register.html")

        if not email or len(email) > 255:
            flash("Enter a valid email address.", "error")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT user_id FROM users WHERE email = %s",
                (email,)
            )

            if cursor.fetchone():
                flash("This email is already registered.", "error")
                return render_template("register.html")

            cursor.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (%s, %s, %s)
                """,
                (name, email, hash_password(password))
            )

            connection.commit()

            flash("Account created successfully. Please log in.", "success")
            return redirect(url_for("login"))

        except mysql.connector.Error:
            connection.rollback()
            app.logger.exception("Registration database error")
            flash("Could not create the account. Please try again.", "error")

        finally:
            cursor.close()
            connection.close()

    return render_template("register.html")


# --------------------------------------------------
# Login
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("todos"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute(
                """
                SELECT user_id, name, email, password_hash
                FROM users
                WHERE email = %s
                """,
                (email,)
            )

            user = cursor.fetchone()

            if user and verify_password(user["password_hash"], password):
                # Upgrade an old Werkzeug hash to bcrypt.
                if not user["password_hash"].startswith(
                    ("$2a$", "$2b$", "$2y$")
                ):
                    cursor.execute(
                        """
                        UPDATE users
                        SET password_hash = %s
                        WHERE user_id = %s
                        """,
                        (hash_password(password), user["user_id"])
                    )
                    connection.commit()

                session.clear()
                session["user_id"] = user["user_id"]
                session["user_name"] = user["name"]

                flash("Welcome back!", "success")
                return redirect(url_for("todos"))

            flash("Invalid email or password.", "error")

        except mysql.connector.Error:
            app.logger.exception("Login database error")
            flash("Could not log in. Please try again.", "error")

        finally:
            cursor.close()
            connection.close()

    return render_template("login.html")


# --------------------------------------------------
# Logout
# --------------------------------------------------

@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out.", "success")
    return redirect(url_for("login"))


# --------------------------------------------------
# To-Do list
# --------------------------------------------------

@app.route("/todos")
@login_required
def todos():
    user_id = session["user_id"]
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "all")

    if status not in ("all", "open", "done"):
        status = "all"

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        sql = """
            SELECT todo_id, user_id, title, description,
                   is_done, created_at, due_date
            FROM todos
            WHERE user_id = %s
        """
        params = [user_id]

        if search:
            sql += " AND (title LIKE %s OR description LIKE %s)"
            params.extend([f"%{search}%", f"%{search}%"])

        if status == "open":
            sql += " AND is_done = 0"
        elif status == "done":
            sql += " AND is_done = 1"

        sql += """
            ORDER BY is_done ASC, due_date IS NULL,
                     due_date ASC, created_at DESC
        """

        cursor.execute(sql, tuple(params))
        todo_list = cursor.fetchall()

        # Calculate task statistics
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(
                    SUM(CASE WHEN is_done = 1 THEN 1 ELSE 0 END), 0
                ) AS done,
                COALESCE(
                    SUM(CASE WHEN is_done = 0 THEN 1 ELSE 0 END), 0
                ) AS open
            FROM todos
            WHERE user_id = %s
            """,
            (user_id,)
        )

        counts = cursor.fetchone()

        return render_template(
            "todos.html",
            todos=todo_list,
            search=search,
            status=status,
            counts=counts,
            user=get_current_user()
        )

    finally:
        cursor.close()
        connection.close()



# --------------------------------------------------
# Add a task
# --------------------------------------------------

@app.route("/todos/add", methods=["GET", "POST"])
@login_required
def add_todo():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        due_date = request.form.get("due_date", "").strip() or None

        if not title or len(title) > 200:
            flash("Enter a task title of up to 200 characters.", "error")
            return render_template("todo_form.html", todo=None)

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO todos (user_id, title, description, due_date)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    session["user_id"],
                    title,
                    description or None,
                    due_date
                )
            )
            connection.commit()

            flash("Task added successfully.", "success")
            return redirect(url_for("todos"))

        except mysql.connector.Error:
            connection.rollback()
            app.logger.exception("Add task database error")
            flash("Could not add the task.", "error")

        finally:
            cursor.close()
            connection.close()

    return render_template("todo_form.html", todo=None)


# --------------------------------------------------
# Edit a task
# --------------------------------------------------

@app.route("/todos/<int:todo_id>/edit", methods=["GET", "POST"])
@login_required
def edit_todo(todo_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM todos WHERE todo_id = %s AND user_id = %s",
            (todo_id, session["user_id"])
        )
        todo = cursor.fetchone()

        if not todo:
            abort(404)

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            due_date = request.form.get("due_date", "").strip() or None

            if not title or len(title) > 200:
                flash("Enter a valid task title.", "error")
                return render_template("todo_form.html", todo=todo)

            cursor.execute(
                """
                UPDATE todos
                SET title = %s, description = %s, due_date = %s
                WHERE todo_id = %s AND user_id = %s
                """,
                (
                    title,
                    description or None,
                    due_date,
                    todo_id,
                    session["user_id"]
                )
            )
            connection.commit()

            flash("Task updated successfully.", "success")
            return redirect(url_for("todos"))

        return render_template("todo_form.html", todo=todo)

    finally:
        cursor.close()
        connection.close()


# --------------------------------------------------
# Toggle task status
# --------------------------------------------------

@app.route("/todos/<int:todo_id>/toggle", methods=["POST"])
@login_required
def toggle_todo(todo_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
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
            abort(404)

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("todos"))


# --------------------------------------------------
# Delete a task
# --------------------------------------------------

@app.route("/todos/<int:todo_id>/delete", methods=["POST"])
@login_required
def delete_todo(todo_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "DELETE FROM todos WHERE todo_id = %s AND user_id = %s",
            (todo_id, session["user_id"])
        )
        connection.commit()

        if cursor.rowcount:
            flash("Task deleted successfully.", "success")
        else:
            abort(404)

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("todos"))


# --------------------------------------------------
# Books list and search
# --------------------------------------------------


@app.route("/books")
@login_required
def books():
    search = request.args.get("q", "").strip()
    min_price = request.args.get("min_price", "").strip()
    max_price = request.args.get("max_price", "").strip()
    category_id = request.args.get("category_id", "").strip()

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        sql = """
            SELECT b.book_id, b.title, b.price, b.author_id,
                   b.cover_image, b.publish_year,
                   a.name AS author_name,
                   p.name AS publisher_name,
                   c.name AS category_name, b.category_id
            FROM BOOK b
            LEFT JOIN AUTHOR a ON b.author_id = a.author_id
            LEFT JOIN PUBLISHER p ON b.publisher_id = p.publisher_id
            LEFT JOIN CATEGORY c ON b.category_id = c.category_id
            WHERE 1=1
        """

        params = []

        if search:
            sql += " AND b.title LIKE %s"
            params.append(f"%{search}%")

        if min_price:
            sql += " AND b.price >= %s"
            params.append(min_price)

        if max_price:
            sql += " AND b.price <= %s"
            params.append(max_price)

        if category_id:
            sql += " AND b.category_id = %s"
            params.append(category_id)

        sql += " ORDER BY b.price ASC"

        cursor.execute(sql, tuple(params))
        book_list = cursor.fetchall()

        cursor.execute("SELECT category_id, name FROM CATEGORY ORDER BY name")
        categories = cursor.fetchall()

        return render_template(
            "books.html",
            books=book_list,
            search=search,
            min_price=min_price,
            max_price=max_price,
            category_id=category_id,
            categories=categories
        )

    finally:
        cursor.close()
        connection.close()


# --------------------------------------------------
# Add and edit books
# --------------------------------------------------

@app.route("/books/add", methods=["GET", "POST"])
@login_required
def add_book():
    return book_form()


@app.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
@login_required
def edit_book(book_id):
    return book_form(book_id)



def book_form(book_id=None):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    old_cover = None

    try:
        book = None

        # Get the book when editing
        if book_id is not None:
            cursor.execute(
                "SELECT * FROM BOOK WHERE book_id = %s",
                (book_id,)
            )
            book = cursor.fetchone()

            if not book:
                abort(404)

            old_cover = book.get("cover_image")

        # Get authors, publishers, and categories
        cursor.execute("SELECT author_id, name FROM AUTHOR ORDER BY name")
        author_list = cursor.fetchall()

        cursor.execute(
            "SELECT publisher_id, name FROM PUBLISHER ORDER BY name"
        )
        publisher_list = cursor.fetchall()

        cursor.execute(
            "SELECT category_id, name FROM CATEGORY ORDER BY name"
        )
        category_list = cursor.fetchall()
        
        
        print("PUBLISHERS:", publisher_list)
        print("CATEGORIES:", category_list)

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            price_text = request.form.get("price", "").strip()
            author_id = request.form.get("author_id", "").strip()
            publish_year_text = request.form.get("publish_year", "").strip()
            publisher_id = request.form.get("publisher_id", "").strip()
            category_id = request.form.get("category_id", "").strip()
            upload = request.files.get("cover_image")

            # Validate title
            if not title or len(title) > 150:
                flash("Enter a valid book title.", "error")
                return render_template(
                    "book_form.html",
                    book=book,
                    authors=author_list,
                    publishers=publisher_list,
                    categories=category_list
                )

            # Validate price
            try:
                price = float(price_text)
                if price < 0:
                    raise ValueError
            except (ValueError, TypeError):
                flash("Enter a valid non-negative price.", "error")
                return render_template(
                    "book_form.html",
                    book=book,
                    authors=author_list,
                    publishers=publisher_list,
                    categories=category_list
                )

            # Validate author
            try:
                author_id = int(author_id)
            except (ValueError, TypeError):
                flash("Please select an author.", "error")
                return render_template(
                    "book_form.html",
                    book=book,
                    authors=author_list,
                    publishers=publisher_list,
                    categories=category_list
                )

            if not any(a["author_id"] == author_id for a in author_list):
                flash("The selected author does not exist.", "error")
                return render_template(
                    "book_form.html",
                    book=book,
                    authors=author_list,
                    publishers=publisher_list,
                    categories=category_list
                )

            # Validate publish year (optional)
            if publish_year_text:
                try:
                    publish_year = int(publish_year_text)
                    if publish_year <= 0:
                        raise ValueError
                except (ValueError, TypeError):
                    flash("Enter a valid publish year.", "error")
                    return render_template(
                        "book_form.html",
                        book=book,
                        authors=author_list,
                        publishers=publisher_list,
                        categories=category_list
                    )
            else:
                publish_year = None

            # Validate publisher
            try:
                publisher_id = int(publisher_id)
            except (ValueError, TypeError):
                flash("Please select a publisher.", "error")
                return render_template(
                    "book_form.html",
                    book=book,
                    authors=author_list,
                    publishers=publisher_list,
                    categories=category_list
                )

            if not any(
                p["publisher_id"] == publisher_id
                for p in publisher_list
            ):
                flash("The selected publisher does not exist.", "error")
                return render_template(
                    "book_form.html",
                    book=book,
                    authors=author_list,
                    publishers=publisher_list,
                    categories=category_list
                )

            # Validate category
            try:
                category_id = int(category_id)
            except (ValueError, TypeError):
                flash("Please select a category.", "error")
                return render_template(
                    "book_form.html",
                    book=book,
                    authors=author_list,
                    publishers=publisher_list,
                    categories=category_list
                )

            if not any(
                c["category_id"] == category_id
                for c in category_list
            ):
                flash("The selected category does not exist.", "error")
                return render_template(
                    "book_form.html",
                    book=book,
                    authors=author_list,
                    publishers=publisher_list,
                    categories=category_list
                )

            # Save the uploaded cover image
            try:
                new_cover = save_image(upload)
            except ValueError as error:
                flash(str(error), "error")
                return render_template(
                    "book_form.html",
                    book=book,
                    authors=author_list,
                    publishers=publisher_list,
                    categories=category_list
                )

            cover_to_save = new_cover or old_cover

            # Add a new book
            if book_id is None:
                cursor.execute(
                    """
                    INSERT INTO BOOK
                    (title, price, author_id, cover_image,
                     publish_year, publisher_id, category_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        title, price, author_id, cover_to_save,
                        publish_year, publisher_id, category_id
                    )
                )

            # Update an existing book
            else:
                cursor.execute(
                    """
                    UPDATE BOOK
                    SET title = %s,
                        price = %s,
                        author_id = %s,
                        cover_image = %s,
                        publish_year = %s,
                        publisher_id = %s,
                        category_id = %s
                    WHERE book_id = %s
                    """,
                    (
                        title, price, author_id, cover_to_save,
                        publish_year, publisher_id, category_id, book_id
                    )
                )

            connection.commit()

            if new_cover and old_cover:
                delete_image(old_cover)

            flash("Book saved successfully.", "success")
            return redirect(url_for("books"))

        return render_template(
            "book_form.html",
            book=book,
            authors=author_list,
            publishers=publisher_list,
            categories=category_list
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()



# --------------------------------------------------
# Delete a book
# --------------------------------------------------

@app.route("/books/<int:book_id>/delete", methods=["POST"])
@login_required
def delete_book(book_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT cover_image FROM BOOK WHERE book_id = %s",
            (book_id,)
        )
        book = cursor.fetchone()

        if not book:
            abort(404)

        cursor.execute("DELETE FROM BOOK WHERE book_id = %s", (book_id,))
        connection.commit()

        delete_image(book["cover_image"])
        flash("Book deleted successfully.", "success")

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("books"))


# --------------------------------------------------
# Authors list and search
# --------------------------------------------------

@app.route("/authors")
@login_required
def authors():
    search = request.args.get("search", "").strip()

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        sql = """
            SELECT a.author_id, a.name, a.country, a.photo,
                   COUNT(b.book_id) AS book_count
            FROM AUTHOR a
            LEFT JOIN BOOK b ON b.author_id = a.author_id
        """
        params = []

        if search:
            sql += " WHERE a.name LIKE %s OR a.country LIKE %s"
            params.extend([f"%{search}%", f"%{search}%"])

        sql += """
            GROUP BY a.author_id, a.name, a.country, a.photo
            ORDER BY a.name
        """

        cursor.execute(sql, tuple(params))
        author_list = cursor.fetchall()

        return render_template(
            "authors.html",
            authors=author_list,
            search=search
        )

    finally:
        cursor.close()
        connection.close()


# --------------------------------------------------
# Add and edit authors
# ------------boo--------------------------------------

@app.route("/authors/add", methods=["GET", "POST"])
@login_required
def add_author():
    return author_form()


@app.route("/authors/<int:author_id>/edit", methods=["GET", "POST"])
@login_required
def edit_author(author_id):
    return author_form(author_id)


def author_form(author_id=None):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    old_photo = None

    try:
        author = None

        if author_id is not None:
            cursor.execute(
                "SELECT * FROM AUTHOR WHERE author_id = %s",
                (author_id,)
            )
            author = cursor.fetchone()

            if not author:
                abort(404)

            old_photo = author.get("photo")

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            country = request.form.get("country", "").strip()
            upload = request.files.get("photo")

            if not name or len(name) > 100:
                flash("Enter an author name of up to 100 characters.", "error")
                return render_template("author_form.html", author=author)

            try:
                new_photo = save_image(upload)
            except ValueError as error:
                flash(str(error), "error")
                return render_template("author_form.html", author=author)

            photo_to_save = new_photo or old_photo

            if author_id is None:
                cursor.execute(
                    """
                    INSERT INTO AUTHOR (name, country, photo)
                    VALUES (%s, %s, %s)
                    """,
                    (name, country or None, photo_to_save)
                )
            else:
                cursor.execute(
                    """
                    UPDATE AUTHOR
                    SET name = %s, country = %s, photo = %s
                    WHERE author_id = %s
                    """,
                    (name, country or None, photo_to_save, author_id)
                )

            connection.commit()

            if new_photo and old_photo:
                delete_image(old_photo)

            flash("Author saved successfully.", "success")
            return redirect(url_for("authors"))

        return render_template("author_form.html", author=author)

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


# --------------------------------------------------
# Delete an author and their books
# --------------------------------------------------

@app.route("/authors/<int:author_id>/delete", methods=["POST"])
@login_required
def delete_author(author_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT photo FROM AUTHOR WHERE author_id = %s",
            (author_id,)
        )
        author = cursor.fetchone()

        if not author:
            abort(404)

        cursor.execute(
            "SELECT cover_image FROM BOOK WHERE author_id = %s",
            (author_id,)
        )
        book_images = cursor.fetchall()

        cursor.execute(
            "DELETE FROM AUTHOR WHERE author_id = %s",
            (author_id,)
        )
        connection.commit()

        delete_image(author["photo"])

        for item in book_images:
            delete_image(item["cover_image"])

        flash("Author and their books deleted successfully.", "success")

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("authors"))



# --------------------------------------------------
# Reports
# --------------------------------------------------

@app.route("/reports")
@login_required
def reports():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Report 1: Number of books and average price per category
        cursor.execute("""
            SELECT
                c.category_id,
                c.name AS category_name,
                COUNT(b.book_id) AS book_count,
                COALESCE(AVG(b.price), 0) AS average_price
            FROM CATEGORY c
            LEFT JOIN BOOK b ON c.category_id = b.category_id
            GROUP BY c.category_id, c.name
            ORDER BY c.name
        """)
        category_reports = cursor.fetchall()

        # Report 2: Authors who have at least 2 books
        cursor.execute("""
            SELECT
                a.author_id,
                a.name AS author_name,
                COUNT(b.book_id) AS book_count
            FROM AUTHOR a
            INNER JOIN BOOK b ON a.author_id = b.author_id
            GROUP BY a.author_id, a.name
            HAVING COUNT(b.book_id) >= 2
            ORDER BY book_count DESC
        """)
        author_reports = cursor.fetchall()

        # Report 3: General book price statistics
        cursor.execute("""
            SELECT
                COUNT(*) AS total_books,
                COALESCE(SUM(price), 0) AS total_price,
                COALESCE(AVG(price), 0) AS average_price,
                COALESCE(MIN(price), 0) AS minimum_price,
                COALESCE(MAX(price), 0) AS maximum_price
            FROM BOOK
        """)
        price_reports = cursor.fetchone()
        
        
        # Report 4: All authors and their number of books
        cursor.execute("""
            SELECT
                a.author_id,
                a.name AS author_name,
                COUNT(b.book_id) AS book_count
            FROM AUTHOR a
            LEFT JOIN BOOK b ON a.author_id = b.author_id
            GROUP BY a.author_id, a.name
            ORDER BY a.name
        """)
        all_author_reports = cursor.fetchall()

        # Report 5: Books where author and publisher are from the same country
        cursor.execute("""
            SELECT
                b.book_id,
                b.title AS book_title,
                a.name AS author_name,
                a.country AS author_country,
                p.name AS publisher_name,
                p.country AS publisher_country
            FROM BOOK b
            INNER JOIN AUTHOR a ON b.author_id = a.author_id
            INNER JOIN PUBLISHER p ON b.publisher_id = p.publisher_id
            WHERE a.country IS NOT NULL
              AND p.country IS NOT NULL
              AND a.country = p.country
            ORDER BY b.title
        """)
        same_country_books = cursor.fetchall()


        
        return render_template(
            "reports.html",
            category_reports=category_reports,
            author_reports=author_reports,
            price_reports=price_reports,
            all_author_reports=all_author_reports,
            same_country_books=same_country_books
        )


    finally:
        cursor.close()
        connection.close()



# --------------------------------------------------
# Loans Reports
# --------------------------------------------------

@app.route("/loans")
@login_required
def loans():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Report 1: Unreturned loans
        cursor.execute("""
            SELECT
                l.loan_id,
                b.title AS book_title,
                m.name AS member_name,
                l.loan_date,
                l.return_date
            FROM LOAN l
            INNER JOIN BOOK b ON l.book_id = b.book_id
            INNER JOIN MEMBER m ON l.member_id = m.member_id
            WHERE l.return_date IS NULL
            ORDER BY l.loan_date
        """)
        unreturned_loans = cursor.fetchall()

        # Report 2: Members who never borrowed a book
        cursor.execute("""
            SELECT
                m.member_id,
                m.name AS member_name,
                m.email
            FROM MEMBER m
            LEFT JOIN LOAN l ON m.member_id = l.member_id
            WHERE l.loan_id IS NULL
            ORDER BY m.name
        """)
        members_never_borrowed = cursor.fetchall()

        # Report 3: Books that were never borrowed
        cursor.execute("""
            SELECT
                b.book_id,
                b.title AS book_title,
                b.price
            FROM BOOK b
            LEFT JOIN LOAN l ON b.book_id = l.book_id
            WHERE l.loan_id IS NULL
            ORDER BY b.title
        """)
        
        books_never_borrowed = cursor.fetchall()

        # Report 4: Top 3 most borrowed books
        cursor.execute("""
            SELECT
                b.book_id,
                b.title AS book_title,
                COUNT(l.loan_id) AS borrow_count
            FROM BOOK b
            INNER JOIN LOAN l ON b.book_id = l.book_id
            GROUP BY b.book_id, b.title
            ORDER BY borrow_count DESC, b.title
            LIMIT 3
        """)
        most_borrowed_books = cursor.fetchall()

        # Report 5: Member with the most loans
        cursor.execute("""
            SELECT
                m.member_id,
                m.name AS member_name,
                COUNT(l.loan_id) AS loan_count
            FROM MEMBER m
            INNER JOIN LOAN l ON m.member_id = l.member_id
            GROUP BY m.member_id, m.name
            ORDER BY loan_count DESC, m.name
            LIMIT 1
        """)
        most_active_member = cursor.fetchone()

        
        return render_template(
            "loans.html",
            unreturned_loans=unreturned_loans,
            members_never_borrowed=members_never_borrowed,
            books_never_borrowed=books_never_borrowed,
            most_borrowed_books=most_borrowed_books,
            most_active_member=most_active_member
        )


    finally:
        cursor.close()
        connection.close()



# --------------------------------------------------
# Error handlers
# --------------------------------------------------

@app.errorhandler(404)
def not_found(error):
    return render_template(
        "error.html",
        message="Page not found."
    ), 404


@app.errorhandler(413)
def file_too_large(error):
    return render_template(
        "error.html",
        message="Image size must not exceed 5 MB."
    ), 413


@app.errorhandler(500)
def internal_error(error):
    return render_template(
        "error.html",
        message="An unexpected error occurred. Please try again."
    ), 500


# --------------------------------------------------
# Run application
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)

