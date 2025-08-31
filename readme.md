# UK BusApp – MSc Computer Science Project

## 1. Project Overview

**UK BusApp** is a functional web application developed for an MSc Computer Science project at the University of Birmingham. It provides a complete flow for searching UK bus schedules, user authentication, ticket booking with a simulated payment step, booking management (view/cancel), and an AI-powered assistant to help users with queries.

The application demonstrates full-stack web development with Flask, persistent storage with SQLAlchemy/SQLite, session & CSRF security, automated testing, and integration of third-party AI services.

### Core Features
- **Dynamic Schedule Search:** Filter schedules by **source**, **destination**, and **date**.
- **Secure Authentication:** Register, login, logout, and session management (Flask-Login).
- **Booking System:** Select a trip → enter details → simulated payment → confirmation.
- **User Dashboard:** View booking history and cancel upcoming trips.
- **AI Chatbot Assistant:** Conversational help using **Google Generative AI (Gemini)**.

### Technology Stack
- **Frontend:** Jinja2 templates, Bootstrap 5
- **Backend:** Python, Flask
- **Database:** SQLite via Flask-SQLAlchemy
- **Auth:** Flask-Login (password hashing; session cookies)
- **Security:** CSRF protection with Flask-WTF
- **AI Integration:** `google-generativeai` (Gemini)
- **Testing:** Pytest

---

## 2. Repository Structure

```
MSc Project/
├─ app.py                      # Main Flask application
├─ requirements.txt            # Python dependencies
├─ schedules_full.csv          # Local bus schedules data
├─ templates/                  # Jinja2 templates (Bootstrap UI)
│  ├─ base.html
│  ├─ home.html                # Search form
│  ├─ schedule.html            # Search results
│  ├─ book.html
│  ├─ book_direct.html
│  ├─ process_payment.html     # Simulated payment
│  ├─ confirmation.html
│  ├─ my_bookings.html         # Booking history & cancel
│  ├─ login.html
│  ├─ register.html
│  └─ chatbot.html             # AI assistant UI
├─ tests/
│  └─ test_app.py              # Minimal functional tests
└─ .env                        # Environment variables 
```

 **Note:** The SQLite database (`site.db`) is created automatically on first run.

---

## 3. Getting Started (Step-by-Step)

These steps show how to run the application locally from a fresh clone using **Conda** for isolation.

### Prerequisites
- [Git](https://git-scm.com/downloads)
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Anaconda](https://www.anaconda.com/products/distribution)

### Step 1: Clone the Repository
```
git clone <your-repository-url> (https://git.cs.bham.ac.uk/projects-2024-25/dxr419.git)
cd "<repository-folder-name>"
```

### Step 2: Create and Activate a Conda Environment
```
# Create a clean environment (Python 3.9 is known-good for this project)
conda create --name busapp_env python=3.9 -y

# Activate it
conda activate busapp_env
```

### Step 3: Install Dependencies
```
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Create a **`.env`** file in the project root with the following content:

```ini
# Required for sessions & CSRF; use a long, random string
SECRET_KEY="change_this_to_something_very_long"

# Required for the AI chatbot feature (Gemini)
GOOGLE_API_KEY="your_google_generative_ai_api_key"
```

- The core app (search, booking, etc.) runs without `GOOGLE_API_KEY`; however, the **chatbot** feature requires it.

### Step 5: Run the Application
```
python app.py
```
Open your browser at **http://127.0.0.1:5000**.

---

## 4. How to Use

1. **Home (`/`)** – Enter **From**, **To**, and **Date**, then click **Search**.  
2. **Schedule (`/schedule`)** – View matching routes; click **Book** for a desired trip.  
3. **Auth** – If not logged in, you’ll be prompted to **Register** then **Login**.  
4. **Book (`/book` or `/book_direct`)** – Provide passenger details and continue.  
5. **Payment (`/process_payment`)** – Simulated payment; shows confirmation on success.  
6. **My Bookings (`/my_bookings`)** – Browse upcoming/past bookings; cancel future ones.  
7. **AI Assistant (`/chatbot`)** – Ask questions (e.g., “Birmingham to Leeds tomorrow at noon?”).  

**Tip:** Schedules are loaded from `schedules_full.csv` at startup; results are deterministic and offline.

---

## 5. Configuration Details

- **Database:** SQLite (`sqlite:///site.db`) created automatically at startup.
- **Security:** CSRF protection is enabled. Use in-app forms for POST requests.
- **Ports:** Default Flask port **5000** on `127.0.0.1`.
- **AI Model:** Gemini (configured through `google-generativeai`), initialized from `GOOGLE_API_KEY`.

---

## 6. Useful Endpoints

- `GET /` – Home (search form)  
- `GET /schedule?source=...&destination=...&date=YYYY-MM-DD` – Search results  
- `GET|POST /register` – Create an account  
- `GET|POST /login` – Sign in  
- `GET /logout` – Sign out  
- `GET|POST /book` – Booking flow  
- `GET|POST /process_payment` – Simulated payment step  
- `GET /my_bookings` – Booking history  
- `POST /cancel_booking/<booking_id>` – Cancel a booking  
- `GET /chatbot` – Chatbot UI  
- `POST /chatbot_api` – Chatbot JSON API (requires login & CSRF header)

---

## 7. Running the Test Suite

1. Ensure the **`busapp_env`** environment is active.
2. From the project root, run:
   ```
   pytest
   ```

A successful test run confirms core routes and flows are functioning.

---

## 8. Common Issues & Fixes

- **`ModuleNotFoundError` / missing packages**  
  Activate the Conda env and reinstall deps:  
  `conda activate busapp_env && pip install -r requirements.txt`

- **CSRF errors on POST**  
  Use the provided HTML forms/pages. For API calls, include the `X-CSRFToken` header.

- **Port 5000 already in use**  
  Stop the other process or run via Flask CLI with a different port (e.g., `--port 5001`).

- **Chatbot not responding**  
  Verify `GOOGLE_API_KEY` is set correctly and the machine has internet access.

---

## 9. Note

- Payment is **simulated**—no real transactions occur.  
- Data is loaded from a local CSV, ensuring reproducibility.  
- Passwords are hashed; sessions use `SECRET_KEY`; CSRF is enabled site-wide.  
- Database is created on first run—no manual migrations needed.

---

