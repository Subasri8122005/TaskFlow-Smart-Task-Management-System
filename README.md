# TaskFlow – Smart Task Management System

A web-based task management application built using Python Flask, SQLite, HTML, CSS and JavaScript. TaskFlow helps users organize their daily activities, track progress and manage tasks efficiently.

## Features

- **User Authentication:** User registration, login and logout.
- **Task Management:** Create, view, update and delete tasks.
- **Task Categories:** Organize tasks into Work, Study and Personal.
- **Priority Management:** Set Low, Medium and High priorities.
- **Due Dates:** Assign due dates to tasks.
- **Search and Filter:** Find tasks and filter them by status.
- **Dashboard:** View total, pending, completed and overdue tasks with progress statistics.
- **CSV Export:** Download task information as a CSV file.
- **Dark / Light Mode:** Switch between display themes.
- **Automated Testing:** 9 test cases implemented using Pytest.

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Flask | Web application framework |
| SQLite | Database |
| HTML | Web page structure |
| CSS | Styling and responsive layout |
| JavaScript | Frontend interactions |
| Pytest | Automated testing |
| Git & GitHub | Version control |

## Project Structure

```text
task-manager/
│
├── app.py
├── test_app.py
├── tasks.db
├── README.md
│
├── templates/
│   └── index.html
│
├── static/
│   ├── style.css
│   └── script.js
│
└── venv/
```

## Installation and Setup

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd task-manager
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the virtual environment

**Windows PowerShell:**

```powershell
.\venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
python -m pip install Flask pytest
```

### 5. Run the application

```bash
python app.py
```

Open your browser and visit:

```text
http://127.0.0.1:5000/
```

## Automated Testing

Run the test suite using:

```bash
python -m pytest -v
```

### Test Results

- Total test cases: 9
- Passed: 9
- Failed: 0

The test cases cover user registration, duplicate registration, login, authentication, task creation, task updates, task deletion, dashboard statistics and CSV export.

## Learning Outcomes

- Developed a full-stack web application using Flask.
- Practiced database operations with SQLite.
- Implemented user authentication and session management.
- Built REST-style API endpoints.
- Learned automated testing using Pytest.
- Practiced project organization and version control.

## Author

**Subasri S**

B.Tech – Information Technology

GitHub: https://github.com/Subasri8122005

---

*TaskFlow – Organize your tasks. Track your progress. Achieve your goals.*