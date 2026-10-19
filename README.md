# EduCareNix — Smart Learning Platform

EduCareNix is a Flask-based learning platform for students. It brings structured courses, lessons, quizzes, progress tracking, badges, certificates, and an AI study assistant together in one web application.

**Live demo:** [educarenix.onrender.com](https://educarenix.onrender.com)

> The live demo is hosted on Render's free tier. The service may take a short time to wake after inactivity, and its SQLite database and uploaded files are not durable across restarts or redeploys. Use test data only.

## Features

* **Student accounts:** sign up, log in, edit a profile, upload a profile photo, and change a password.
* **Courses and lessons:** browse courses, study lesson content, and mark lessons complete.
* **Quizzes:** answer course questions, view results, and track quiz attempts.
* **Progress and achievements:** monitor learning activity and earn badges.
* **Certificates:** view certificates and verify certificate records.
* **Course reviews:** submit and manage course reviews.
* **Admin dashboard:** manage students, courses, lessons, quizzes, questions, badges, and reviews.
* **AI study assistant:** ask educational questions through the Gemini API. The API key is read from the `GEMINI\_API\_KEY` environment variable.
* **Responsive interface:** Flask templates with custom CSS for desktop and mobile layouts.

## Technology

* Python and Flask
* SQLite
* HTML, CSS, and JavaScript
* Google Gemini API for AI responses
* Gunicorn for production serving
* Render for the hosted demo

## Run locally

### Requirements

* Python 3.10 or later
* `pip`
* A Gemini API key if you want to use the AI assistant

### Setup

Clone the repository and enter the project folder:

```bash
git clone https://github.com/asrafali9531/EduCareNix.git
cd EduCareNix
```

Create and activate a virtual environment.

**Windows PowerShell:**

```powershell
py -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Set the Gemini API key in your terminal session. Replace the placeholder locally; never commit the real key to GitHub.

**Windows PowerShell:**

```powershell
$env:GEMINI\_API\_KEY = "YOUR\_GEMINI\_API\_KEY"
```

**macOS / Linux:**

```bash
export GEMINI\_API\_KEY="YOUR\_GEMINI\_API\_KEY"
```

Start the development server:

```bash
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser. If `GEMINI\_API\_KEY` is not set, the main learning features can still be explored, but AI responses will not work.

## Deploy to Render

1. Push the project to a GitHub repository.
2. In Render, create a **Web Service** and connect the repository.
3. Set the build command to:

```text
   pip install -r requirements.txt
   ```

4. Set the start command to:

```text
   gunicorn app:app
   ```

5. In the Render service's **Environment** settings, add `GEMINI\_API\_KEY` with your Gemini API key as its value. Keep the key out of source code and Git history.
6. Deploy the service. Render will provide a public `onrender.com` URL.

The application initializes its SQLite tables on startup. For a production deployment, use a persistent managed database and durable object storage for uploads instead of relying on a free instance's local filesystem.

## Data and security notes

* **SQLite on free Render is temporary storage.** User accounts, course progress, reviews, quiz attempts, certificates, and uploaded profile images can be lost when the service restarts, sleeps, or redeploys. Do not use the free demo for important or real user data.
* **Protect API keys.** Store `GEMINI\_API\_KEY` in the host's secret/environment-variable settings. Never put it in `app.py`, templates, JavaScript, screenshots, or a committed `.env` file.
* **Change development credentials.** Replace any sample or seeded administrator credentials and the Flask session secret before sharing or deploying the code publicly.
* **Use HTTPS and production settings.** Keep Flask debug mode disabled on the public deployment.
* **AI privacy.** Do not send passwords, student records, or other sensitive personal data to the AI assistant. Free API quotas and model availability may change; check the provider's current terms and limits.

## Suggested improvements

* Move from SQLite to a persistent PostgreSQL database for production.
* Store profile images and other uploads in durable object storage.
* Add automated tests for authentication, lessons, quizzes, and certificate verification.
* Add rate limiting and stronger CSRF protection to public forms and the AI endpoint.
* Add screenshots or a short demo video to the repository once the UI is finalized.

## Repository structure

```text
EduCareNix/
├── app.py
├── requirements.txt
├── static/
│   ├── style.css
│   └── ...
└── templates/
    ├── base.html
    └── ...
```

## License

No license is specified yet. Add a `LICENSE` file before allowing others to reuse, modify, or redistribute the project.

