# Login & To-Do Application

## Project Overview

This project is a web-based Login and To-Do List application developed using Python, Flask, and MySQL. It allows users to create accounts, log in securely, and manage their personal tasks.

## Features

* User registration with email and password.
* Secure password hashing using bcrypt.
* Login and logout functionality.
* Session-based user authentication.
* Add new tasks.
* Edit existing tasks.
* Mark tasks as completed or open.
* Delete tasks.
* Store user accounts and tasks in a MySQL database.
* Users can only manage their own tasks.

## Technologies Used

* **Python** – Backend programming language.
* **Flask** – Web framework.
* **MySQL** – Database management system.
* **mysql-connector-python** – MySQL database connection.
* **bcrypt** – Password hashing.
* **python-dotenv** – Environment variable management.
* **HTML/CSS** – Frontend structure and styling.

## Project Structure

```text
DB LAB2/
│
├── app.py
├── .env
├── .gitignore
├── README.md
│
├── templates/
│   ├── login.html
│   ├── register.html
│   └── todos.html
│
├── static/
│   └── style.css
│
└── venv/
```

## Database Setup

Create a MySQL database named `registration` and create the required tables:

### Users Table

Stores user account information, including email, name, and password hash.

### Todos Table

Stores tasks associated with each user, including the task title, completion status, and creation date.

Make sure the database tables and columns match those used in `app.py`.

## Installation and Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd "DB LAB2"
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

### 3. Activate the Virtual Environment

**Windows PowerShell:**

```powershell
.\venv\Scripts\Activate.ps1
```

### 4. Install Dependencies

```bash
pip install Flask mysql-connector-python bcrypt python-dotenv
```

### 5. Configure Environment Variables

Create a `.env` file in the project root directory:

```env
SECRET_KEY=your_secret_key
MYSQL_PASSWORD=your_mysql_password
```

Replace the example values with your own secret key and MySQL password.

### 6. Run the Application

```bash
python app.py
```

### 7. Open the Application

Open your browser and visit:

```text
http://127.0.0.1:5000
```

Register an account or log in to start managing your tasks.

## Security Notes

* Passwords are stored as hashes rather than plain text.
* Environment variables are used for configuration.
* Each user's task operations are restricted to their own records.
* Do not upload your `.env` file or database credentials to GitHub.

## Author

Developed as a Python Flask and MySQL web application project.
