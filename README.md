<h1 align="center">🚌 Matatu Booking & Scheduling System</h1>

<p align="center">
  <strong>A modern, responsive Django web app for managing and booking matatu trips across Kenya.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Django-4.x-green?logo=django" alt="Django">
  <img src="https://img.shields.io/badge/Database-SQLite-blue?logo=sqlite">
  <img src="https://img.shields.io/badge/UI-TailwindCSS-blueviolet?logo=tailwindcss">
  <img src="https://img.shields.io/badge/License-MIT-yellow">
</p>

---

## ✨ Overview

This system allows passengers to:

- 🪪 Register and log in
- 🗓️ View available matatu trips
- 🎟️ Book seats in real time (no overbooking!)

Admins and operators can:

- 🚐 Add & manage matatus and trip schedules
- 📋 Monitor all bookings
- 🧑‍💼 Manage user roles

---

## 🔥 Key Features

- ✅ **Secure Authentication** (Register/Login)
- ✅ **Matatu & Trip Management** (Admin side)
- ✅ **Real-Time Seat Booking** with availability check
- ✅ **Duplicate Booking Prevention**
- ✅ **Modern UI** with Tailwind CSS
- ✅ **Role-based Dashboard**
- ✅ **Mobile Responsive** & Fast

---

## ⚙️ Tech Stack

| Layer       | Technology              |
|-------------|--------------------------|
| Backend     | [Django](https://www.djangoproject.com/) (Python) |
| Frontend    | HTML + Tailwind CSS + JS |
| Database    | SQLite (dev) / PostgreSQL (prod-ready) |
| Auth        | Django's built-in system |

---

## 🧩 Project Structure

Matatu/
├── matatu/ # Main app
│ ├── templates/
│ │ └── matatu/ # HTML pages
│ ├── static/
│ │ └── css/ # Tailwind CSS
│ ├── models.py # Booking, Matatu, Trip models
│ ├── views.py # Main views
│ ├── urls.py # App routes
│ ├── forms.py # User/forms
│ └── admin.py # Admin registration
│
├── Matatu/ # Django project
│ ├── settings.py
│ ├── urls.py
│ └── wsgi.py
│
├── db.sqlite3 # SQLite DB (for development)
├── manage.py
└── README.md


---

## 🚀 Quick Start

### 🔧 Setup & Run Locally


# 1. Clone the repo
git clone https://github.com/ayagah/Matatu.git
cd Matatu

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Apply migrations
python manage.py migrate

# 5. Create superuser for admin access
python manage.py createsuperuser

6. Start the server
python manage.py runserver
