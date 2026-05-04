<<<<<<< HEAD
# biz-light
=======
# Biz-ight 🚀
### AI-Powered Decision Support & Automation Dashboard for Micro-Businesses

Biz-ight is a production-ready full-stack application designed to help micro and home-based businesses manage inventory, track finances, and get AI-driven insights.

## Features
- **Dashboard**: Real-time KPIs (BHS, RGR, ITR, ER, SCP) with trend visualizations.
- **Inventory Management**: Product catalog with automated low-stock alerts.
- **Financial Logging**: Simple interface for logging sales and expenses.
- **Rule-Engine Automation**: Automatic alerts for inventory and financial anomalies.
- **AI Explanation Layer**: Natural language summaries of business health using Gemini AI.
- **Modular Architecture**: Clean Django MVC structure with MongoDB.

## Tech Stack
- **Backend**: Django 4.1, Djongo (MongoDB), Celery, Redis.
- **Frontend**: Tailwind CSS, Chart.js, Django Templates.
- **Database**: MongoDB Atlas.
- **AI**: Google Gemini API.

## Setup Instructions

### 1. Prerequisites
- Python 3.10+
- Redis (for Celery background jobs)
- MongoDB account (URI provided in .env)

### 2. Installation
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure the `.env` file (already provided with your credentials).

### 3. Database & Seeding
Run migrations and seed the database with demo data:
```bash
python manage.py migrate
python manage.py seed_data
```

### 4. Running the Application
Start the Django development server:
```bash
python manage.py runserver
```

In separate terminals, start the Celery worker and beat:
```bash
celery -A biz_light worker -l info
celery -A biz_light beat -l info
```

### 5. Docker Setup (Alternative)
If you have Docker installed:
```bash
docker-compose up --build
```

## Folder Structure
- `apps/`: Modular Django applications (dashboard, inventory, finance, etc.).
- `biz_light/`: Project configuration and Celery setup.
- `templates/`: Global and app-specific HTML templates.
- `static/`: Frontend assets.



Username: demo
Password: demo1234


check the proposal.txt and check i all the requirement o the proect are done or not and tell me which needs to be implmented yet    also i have updated the new api key for gemini  its  still gives rate limit issue after retrying multiple times  it may be some other issue resolve it ---- also the alert in the dashboard and the alterpage are not update when i update the inventory they should update like done or resolved also all pages should be update according to the inomation 

test every thing ater the changes and tell me if every thing is working fine
>>>>>>> eb8a424 (code)
hi