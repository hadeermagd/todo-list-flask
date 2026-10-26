To-Do & Library Management System

ABOUT THE PROJECT
This project is a web-based application developed using Python, Flask, and MySQL. It allows users to manage personal tasks and manage a library of books and authors.

FEATURES

1. User Authentication
- User registration and login.
- Secure password hashing.
- Session management.
- Logout functionality.

2. To-Do Management
- Add, edit, and delete tasks.
- Mark tasks as completed or pending.
- Add task descriptions and due dates.
- Display task counters.

3. Book Management
- Add, edit, and delete books.
- Display book titles, authors, and prices.
- Display book cover images.
- Search for books.

4. Author Management
- Add, edit, and delete authors.
- Display author names and countries.
- Display the number of books for each author.

5. Additional Features
- Dark mode.
- MySQL database integration.
- User input validation.
- Simple and user-friendly interface.

TECHNOLOGIES USED
- Python
- Flask
- MySQL
- HTML
- CSS
- JavaScript

DATABASE
The application uses a MySQL database named registration.

The main tables are:
- users: Stores user account information.
- todos: Stores personal tasks.
- AUTHOR: Stores author information.
- BOOK: Stores book information and author relationships.

PROJECT TYPE
Individual Database Lab Project.

INSTALLATION AND SETUP

1. Clone the repository:
git clone YOUR_REPOSITORY_URL

2. Navigate to the project folder:
cd "DB LAB2"

3. Create a virtual environment:
python -m venv .venv

4. Activate the virtual environment on Windows:
.venv\Scripts\Activate.ps1

5. Install the required packages:
pip install -r requirements.txt

6. Configure the database:
- Open MySQL Workbench.
- Create or configure the registration database.
- Execute the SQL scripts in the database folder.
- Configure your database credentials in the .env file.

7. Run the application:
python app.py

8. Open the following URL in your browser:
http://127.0.0.1:5000

SECURITY NOTE
Do not upload the .env file or share your database credentials.

AUTHOR
Developed individually as a Database Lab project using Flask and MySQL.
