# Biz-Light

### AI-Powered Business Co-Manager for Micro-Businesses

Biz-Light is a full-stack Django application designed to help micro and home-based businesses manage inventory, finances, alerts, and AI-driven insights in one place.

## Features
- Dashboard with KPI tracking and trend summaries
- Inventory management with stock and low-stock alerts
- Finance logging for sales and expenses
- Automation rules for generated alerts
- AI explanation layer for business insights
- Store integration support for syncing external sales data

## Tech Stack
- Backend: Django, Celery, Redis
- Frontend: Django templates, Tailwind CSS, Chart.js
- Database: MongoDB via Djongo
- AI: Google Gemini API

## Setup Instructions

### 1. Prerequisites
- Python 3.10+
- Redis (for Celery background jobs)
- MongoDB account or local MongoDB setup

### 2. Installation
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure your environment variables in `.env`.

### 3. Database & Seed Data
Run migrations and seed demo data:
```bash
python manage.py migrate
python manage.py seed_data
```

### 4. Running the Application
Start the Django server:
```bash
python manage.py runserver
```

Run Celery workers in separate terminals:
```bash
celery -A biz_light worker -l info
celery -A biz_light beat -l info
```

### 5. Docker Setup (Optional)
If Docker is available:
```bash
docker-compose up --build
```

## Folder Structure
- `apps/` — modular Django apps for dashboard, inventory, finance, automation, and accounts
- `biz_light/` — project configuration and Celery setup
- `templates/` — HTML templates for the web UI
- `static/` — frontend static assets

## Demo Credentials
- Username: `demo`
- Password: `demo1234`

## Notes
For the full project documentation and implementation status, see [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md).
