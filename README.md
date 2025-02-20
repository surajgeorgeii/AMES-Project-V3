# AMES Platform

AMES Platform is a Flask-based web application for academic module evaluation and management.

## Features

- User Authentication and Authorization
- Module Management
- Academic Year Tracking
- Email Notifications
- MongoDB Integration
- Docker Support

## Prerequisites

- Docker and Docker Compose
- Python 3.8+
- MongoDB

## Quick Start

1. Clone the repository:
```bash
git clone <repository-url>
cd AMES-Project-V3
```

2. Create a `.env` file in the app directory with the following variables:
```env
FLASK_APP=run.py
FLASK_DEBUG=true
SECRET_KEY=your_secret_key
MONGO_URI=mongodb://mongo:27017/ames_db
MAIL_SERVER=mailhog
MAIL_PORT=1025
SYSTEM_URL=http://localhost:5000
```

3. Build and run with Docker Compose:
```bash
docker-compose up --build
```

The application will be available at:
- Web Application: http://localhost:5000
- MailHog Interface: http://localhost:8025
- MongoDB: localhost:27017

## Project Structure

```
AMES-Project-V3/
├── app/
│   ├── auth/          # Authentication related code
│   ├── admin/         # Admin panel functionality
│   ├── module_lead/   # Module management
│   ├── base/          # Base templates and utilities
│   ├── templates/     # Jinja2 templates
│   ├── static/        # Static files
│   ├── config.py      # Configuration settings
│   ├── run.py        # Application entry point
│   └── requirements.txt
├── docker-compose.yml
└── README.md
```

## Technology Stack

- **Backend**: Flask
- **Database**: MongoDB
- **Email Testing**: MailHog
- **Authentication**: Flask-Login, Session
- **Frontend**: Jinja2 Templates, Bootstrap
- **Container**: Docker

## Development

To run the application in development mode:

1. Create a virtual environment in the root directory:
```bash
python -m venv .venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows
```

2. Install dependencies:
```bash
pip install -r app/requirements.txt
```

3. Run the application:
```bash
cd app
flask run
```

## API Documentation

The API base URL is `http://localhost:5000/api`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
