# UK BusApp – AI-Assisted Transit Search & Ticket Booking Platform

## 1. Project Overview

**UK BusApp** is a full-stack Python web application engineered as an M.Sc. Computer Science project at the University of Birmingham. The platform provides users with a complete, secure ecosystem to search UK bus schedules, manage accounts, and book tickets via a simulated payment flow, alongside an integrated AI conversational assistant.

The project demonstrates end-to-end software development—combining a scalable Flask backend, robust user authentication, relational database persistence, site-wide security, and third-party LLM orchestration.

### Core Features
- **Schedule Search & Booking Engine:** Multi-step transactional flow allowing users to filter live schedules by source, destination, and date, proceed through a simulated payment gate, and generate booking confirmations.
- **AI Chatbot Assistant:** A conversational help interface powered by the Google Gemini API. It leverages custom context injection to parse natural language user queries and safely route them against local database rules.
- **Secure Authentication & State:** Full user registration, login, and secure session state persistence handled via Flask-Login, featuring encrypted cryptographic password hashing.
- **Site-Wide Security Operations:** Robust cross-site request forgery (CSRF) mitigation implemented across all application forms using Flask-WTF.
- **Automated Regression Testing:** A clean validation suite built with Pytest to systematically test end-to-end user journeys, endpoint stability, and core transaction routes.

### Technical Stack
- **Backend Framework:** Python, Flask 
- **Database Architecture:** SQLite via SQLAlchemy Object-Relational Mapping (ORM)
- **AI Integration:** Google Generative AI SDK (`google-generativeai` / Gemini API)
- **Security & Session Suite:** Flask-Login, Flask-WTF (CSRF Protection), Werkzeug Hashing
- **Testing Engine:** Pytest Framework
- **Frontend Presentation:** Jinja2 Templates, Bootstrap 5 UI

---

## 2. Repository Structure

```
MSc Project/
├─ app.py                      # Main Flask application & orchestration logic
├─ requirements.txt            # Python dependencies
├─ schedules_full.csv          # Structured relational source data
├─ templates/                  # Jinja2 layout ecosystem
│  ├─ base.html
│  ├─ home.html                # Parameterized search vector input
│  ├─ schedule.html            # Data rendering pipeline
│  ├─ book.html
│  ├─ book_direct.html
│  ├─ process_payment.html     # Simulated transaction state
│  ├─ confirmation.html
│  ├─ my_bookings.html         # User dashboard & cancellation logic
│  ├─ login.html
│  ├─ register.html
│  └─ chatbot.html             # Real-time GenAI conversational interface
├─ tests/
│  └─ test_app.py              # Functional endpoint & regression tests
└─ .env                        # Isolated environment variables 
```

**Note:** The SQLite database (`site.db`) is initialized automatically on the application's first runtime execution.

---

## 3. Getting Started (Step-by-Step)

These steps show how to run the application locally from a fresh clone using **Conda** for isolation.

### Prerequisites
- [Git](https://git-scm.com/downloads)
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Anaconda](https://www.anaconda.com/products/distribution)

### Step 1: Clone the Repository
```bash
git clone [https://github.com/devang-0/UK-BusApp-GenAI.git](https://github.com/devang-0/UK-BusApp-GenAI.git)
cd "UK-BusApp-GenAI"
```

### Step 2: Create and Activate a Conda Environment
```bash
# Create a clean environment (Python 3.9 is known-good for this project)
conda create --name busapp_env python=3.9 -y

# Activate it
conda activate busapp_env 
```

### Step 3: Install Dependencies
```bash
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

- The core app runs without `GOOGLE_API_KEY`; however, the **agentic chatbot** feature requires a valid key to communicate with the Gemini API.

### Step 5: Run the Application
```bash
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
7. **AI Assistant (`/chatbot`)** – Ask complex questions (e.g., “Birmingham to Leeds tomorrow at noon?”).  

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
   ```bash
   pytest
   ```

A successful test run confirms core routes and backend validation flows are functioning properly.

---

## 8. Common Issues & Fixes

- **`ModuleNotFoundError` / missing packages** Activate the Conda env and reinstall deps:  
  `conda activate busapp_env && pip install -r requirements.txt`

- **CSRF errors on POST** Use the provided HTML forms/pages. For API calls, include the `X-CSRFToken` header.

- **Port 5000 already in use** Stop the other process or run via Flask CLI with a different port (e.g., `--port 5001`).

- **Chatbot not responding** Verify `GOOGLE_API_KEY` is set correctly and the machine has internet access.

---

## 9. Structural Safety Notes

- Payment mechanics are entirely **simulated**—no real banking data is processed.  
- Data loading is completely local, ensuring testing repeatability and high data-handling speeds.  
- User passwords are securely salted and hashed; sessions utilize an isolated `SECRET_KEY`; token-based CSRF checks are enforced site-wide.
