# Library Management System

A web-based Library Management System developed using **Python, Flask, and MySQL**. The project provides an interface for managing books, authors, members, and borrowing records, along with searching, reporting, and image upload functionality.

## Project Overview

This project was developed as an individual university project. It extends a Flask-based web application to support library management operations and database queries.

## Features

### 1. User Authentication
- User registration and login.
- Secure password hashing.
- Session-based authentication.
- Protected pages for logged-in users.

### 2. Books Management
- Add new books.
- Edit book information.
- Delete books.
- Display the books catalogue.
- Search books by title.
- Filter books by minimum and maximum price.
- Filter books by category.

### 3. Authors Management
- Add new authors.
- Edit author information.
- Delete authors.
- Display authors.
- Upload and display author photos.

### 4. Image Upload
- Upload book cover images.
- Upload author photos.
- Store uploaded images in the static images directory.
- Validate image file types and file sizes.

### 5. Reports
The system provides several database reports, including:
- Number of books and average price per category.
- Authors who have at least two books.
- Book price statistics (COUNT, SUM, AVG, MIN, MAX).
- All authors and their number of books, including authors with no books.
- Books whose authors and publishers are from the same country.

### 6. Loans Management
- Display unreturned loans.
- Find members who have never borrowed a book.
- Find books that have never been borrowed.
- Display the top three most borrowed books.
- Identify the member with the highest number of loans.

### 7. Additional Features
- Dark mode.
- Responsive and user-friendly interface.
- Form validation.
- Database relationships using foreign keys.

## Technologies Used

- **Python**
- **Flask**
- **MySQL**
- **HTML**
- **CSS**
- **JavaScript**
- **Git & GitHub**

## Project Structure

```text
DB LAB2/
│
├── app.py
├── requirements.txt
├── .gitignore
│
├── database/
│   └── schema.sql
│
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── theme.js
│   └── images/
│
└── templates/
    ├── base.html
    ├── login.html
    ├── register.html
    ├── todos.html
    ├── books.html
    ├── book_form.html
    ├── authors.html
    ├── author_form.html
    ├── reports.html
    ├── loans.html
    └── error.html
```

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/hadeermagd/todo-list-flask.git
cd todo-list-flask
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

### 3. Activate the Virtual Environment

**Windows:**

```powershell
.\venv\Scripts\Activate.ps1
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file in the project root directory and configure your local MySQL connection:

```env
SECRET_KEY=your_secret_key
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=registration
```

Replace the example values with your own local configuration.

### 6. Database Configuration

- Make sure MySQL Server is running.
- Create and configure the `registration` database.
- Ensure that the required tables and relationships are created.
- Configure the database connection using the `.env` file.

### 7. Run the Application

```bash
python app.py
```

Open your browser and visit:

```text
http://127.0.0.1:5000
```

## Database Entities

The library database includes the following main entities:

- AUTHOR
- BOOK
- PUBLISHER
- CATEGORY
- MEMBER
- LOAN

The application also uses `users` and `todos` tables for authentication and task management.

## Security Notes

- Passwords are stored as hashes, not plain text.
- Database credentials are stored in environment variables.
- The `.env` file and virtual environment are excluded from Git using `.gitignore`.

## Developer

**Hadeer Abdullah**

Individual University Project

**GitHub Repository:**  
https://github.com/hadeermagd/todo-list-flask

---

*Developed as part of a Database Lab university project.*
