# Organizer - Multi-Purpose Task Manager

A simple yet powerful personal organizer built with Flask and SQLite. It helps you manage your tasks, keep a daily journal, and track your finances in one place.

## Features

### 📋 Tasks
- **CRUD Operations**: Create, view, edit, and delete tasks.
- **Organization**: Set task priority (Low, Medium, High) and deadlines.
- **Filtering**: View tasks by status (All, Active, Completed) or by priority.
- **Overdue Tracking**: Automatically identifies tasks past their deadline.

### 📔 Journal
- **Personal Diary**: Record your thoughts, plans, and daily reflections.
- **Mood Tracking**: Log your mood for each entry with fun icons.
- **Search**: Quickly find old entries using the search bar.

### 💰 Finance
- **Income & Expense Tracker**: Add your transactions with categories.
- **Real-time Balance**: See your current balance, total income, and total expenses.
- **Simple Statistics**: Categorized breakdown of your spending habits.

### 🔐 Security
- **User Authentication**: Secure registration and login system.
- **Privacy**: Each user only has access to their own data.
- **Password Protection**: Uses Werkzeug's secure password hashing.

## Setup & Installation

1. Clone the repository to your local machine.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python app.py
   ```
4. Open your browser and navigate to `http://127.0.0.1:5000/`.

## Technologies Used
- **Backend**: Python (Flask)
- **Database**: SQLite (SQLAlchemy)
- **Frontend**: HTML5, Vanilla CSS, Google Fonts
- **Security**: Werkzeug Security

## Design
The project features a **premium, clean, and responsive design**. It uses a modern CSS grid layout and a custom style system to ensure a great experience on both mobile and desktop devices.
