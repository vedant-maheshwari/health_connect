# HealthConnect Telehealth Platform

<div align="center">

**A comprehensive, microservices-based telehealth platform enabling remote healthcare delivery with multilingual support, AI-powered triage, and offline SMS access.**

[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io/)
[![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=flat&logo=mongodb&logoColor=white)](https://www.mongodb.com/)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Running the Application](#-running-the-application)
- [Development Guide](#-development-guide)
- [API Documentation](#-api-documentation)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌟 Overview

**HealthConnect** is an enterprise-grade telehealth platform designed to bridge the gap between healthcare providers and patients, especially in underserved areas. Built with a modern microservices architecture, the platform offers:

- **Multi-channel Access**: Web interface and offline SMS gateway
- **AI-Powered Health Triage**: Automated wound assessment and clinical documentation
- **Multilingual Support**: Hinglish NLP pipeline for language accessibility
- **Scalable Architecture**: Containerized microservices with independent scaling
- **Real-time Communication**: WebSocket-based chat and notifications

---

## ✨ Features

### Core Capabilities

- 🔐 **Secure Authentication & Authorization** - JWT-based auth with role management (Patient, Doctor, Family, Admin)
- 📅 **Appointment Management** - Real-time slot booking with Redis-based concurrency control
- 💬 **Real-time Chat** - WebSocket-based communication between patients and doctors
- 👨‍👩‍👧 **Family Account Management** - Caregivers can manage patient appointments and records
- 🤖 **AI Wound Triage** - Automated wound assessment with RAG (Retrieval-Augmented Generation)
- 📱 **SMS Gateway** - Offline access via SMS commands (register, book, status, cancel)
- 📊 **Clinical Documentation** - Automated SOAP notes generation
- 🩺 **Blood Signal Processing (BSP)** - ECG analysis and atrial fibrillation detection
- 🔔 **Notification System** - Multi-channel alerts for appointments and updates
- 📋 **Health Records Management** - Comprehensive EHR with AI-generated insights

### Advanced Features

- **Multilingual NLP**: Hinglish support for patient-doctor communication
- **RAG with Clinical Memory**: Context-aware AI responses using historical data
- **Plug-and-Play EHR Integration**: Modular architecture for third-party systems
- **Offline-First Design**: SMS-based appointment booking without internet

---

## 🏗️ Architecture

### System Architecture

The platform follows a **microservices architecture** with the following components:

```
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway (Port 8000)                │
│              (Nginx Reverse Proxy + FastAPI)                │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼──────────────────┐
         │               │                  │
    ┌────▼─────┐   ┌────▼─────┐      ┌────▼─────┐
    │ Auth     │   │ Patient  │      │ Doctor   │
    │ Service  │   │ Service  │      │ Service  │
    │ (8001)   │   │ (8002)   │      │ (8003)   │
    └──────────┘   └──────────┘      └──────────┘
         │               │                  │
    ┌────▼─────┐   ┌────▼─────┐      ┌────▼─────┐
    │Appointment│  │ Family   │      │  Chat    │
    │ Service  │   │ Service  │      │ Service  │
    │ (8004)   │   │ (8005)   │      │ (8006)   │
    └──────────┘   └──────────┘      └──────────┘
         │               │                  │
    ┌────▼─────┐   ┌────▼─────┐      ┌────▼─────┐
    │  Admin   │   │ Records  │      │  Wound   │
    │ Service  │   │ Service  │      │  Triage  │
    │ (8007)   │   │ (8011)   │      │ (8008)   │
    └──────────┘   └──────────┘      └─────┬────┘
         │               │                  │
    ┌────▼─────┐   ┌────▼─────┐      ┌────▼─────┐
    │Notification│ │   SMS    │      │   BSP    │
    │ Service  │   │ Gateway  │      │ Service  │
    │ (8009)   │   │ (8010)   │      │ (8012)   │
    └──────────┘   └──────────┘      └──────────┘
         │               │                  │
    ┌────▼───────────────▼──────────────────▼────┐
    │         Data Layer (Shared Resources)      │
    │  ┌──────────┐  ┌───────┐  ┌──────────┐    │
    │  │PostgreSQL│  │ Redis │  │ MongoDB  │    │
    │  │  (5432)  │  │ (6379)│  │ (27017)  │    │
    │  └──────────┘  └───────┘  └──────────┘    │
    └────────────────────────────────────────────┘
```

### Microservices Breakdown

| Service | Port | Technology | Purpose |
|---------|------|------------|---------|
| **API Gateway** | 8000 | FastAPI | Request routing, authentication, static file serving |
| **Auth Service** | 8001 | FastAPI + PostgreSQL | User registration, login, JWT token management |
| **Patient Service** | 8002 | FastAPI + PostgreSQL | Patient profile management, health records |
| **Doctor Service** | 8003 | FastAPI + PostgreSQL | Doctor profiles, availability, specializations |
| **Appointment Service** | 8004 | FastAPI + PostgreSQL + Redis | Slot management, booking, cancellation with concurrency control |
| **Family Service** | 8005 | FastAPI + PostgreSQL | Family account linking, caregiver access |
| **Chat Service** | 8006 | FastAPI + PostgreSQL | Real-time messaging, WebSocket support |
| **Admin Service** | 8007 | FastAPI + PostgreSQL | Admin dashboard, user management |
| **Wound Triage Service** | 8008 | FastAPI + MongoDB | AI-powered wound assessment, RAG pipeline |
| **Notification Service** | 8009 | FastAPI | Email/SMS notifications, event-driven alerts |
| **SMS Gateway** | 8010 | FastAPI | Offline SMS-based appointment booking |
| **Records Service** | 8011 | FastAPI + PostgreSQL | Clinical notes, SOAP documentation |
| **BSP Service** | 8012 | FastAPI | Blood signal processing, ECG analysis |

---

## 📦 Prerequisites

Before setting up the project, ensure you have the following installed:

### Required Software

- **Docker** (v20.10+) - [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose** (v2.0+) - [Install Docker Compose](https://docs.docker.com/compose/install/)
- **Git** (v2.30+) - [Install Git](https://git-scm.com/downloads)

### Optional (for local development without Docker)

- **Python** (3.9+)
- **PostgreSQL** (15+)
- **MongoDB** (7.0+)
- **Redis** (7.0+)
- **Node.js** (16+) - for frontend tooling (optional)

### API Keys (Optional)

Some features require API keys:
- **OpenAI API Key** - For AI-powered triage and NLP
- **Cohere API Key** - For multilingual embeddings
- **Sarvam API Key** - For Hinglish translation
- **SMS Gateway Credentials** - For SMS-based access

---

## 🚀 Installation

### 1️⃣ Clone the Repository

```bash
git clone <repository-url>
cd telehealth
```

### 2️⃣ Environment Setup

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` to configure your settings:

```bash
# Database Configuration
DATABASE_URL=postgresql://telehealth_user:telehealth_password@postgres:5432/telehealth

# Redis Configuration
REDIS_URL=redis://redis:6379

# JWT Configuration (CHANGE IN PRODUCTION!)
SECRET_KEY=your-super-secret-key-change-this-in-production-make-it-long-and-random
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Optional: AI Service API Keys
OPENAI_API_KEY=your_openai_api_key
COHERE_API_KEY=your_cohere_api_key
SARVAM_API_KEY=your_sarvam_api_key

# Optional: SMS Gateway Configuration
SMS_GATEWAY_URL=http://your-sms-gateway:8080/message
SMS_GATEWAY_USERNAME=your_username
SMS_GATEWAY_PASSWORD=your_password

# Environment
ENVIRONMENT=development
```

> **⚠️ Security Warning**: Never commit your `.env` file to version control. Always use strong, randomly generated values for `SECRET_KEY` in production.

### 3️⃣ Build Docker Images

```bash
docker compose build
```

This will build all microservice images. The process may take 5-10 minutes on first run.

---

## 🔧 Configuration

### Database Initialization

The PostgreSQL database will be automatically initialized on first run. Tables are created via SQLAlchemy models in the `shared/` directory.

### Shared Resources

The `shared/` directory contains common code used across services:

```
shared/
├── __init__.py
├── auth_utils.py      # JWT token creation/validation
├── database.py        # Database connection & session management
├── models.py          # SQLAlchemy ORM models
└── schemas.py         # Pydantic validation schemas
```

### Frontend Configuration

The frontend is served as static files via the API Gateway. Configuration is in `frontend/config.js`:

```javascript
const API_BASE_URL = 'http://localhost:8000';
```

Change this to your production domain when deploying.

---

## ▶️ Running the Application

### Start All Services

```bash
docker compose up
```

Or run in detached mode:

```bash
docker compose up -d
```

### Check Service Health

Wait for all services to be healthy (30-60 seconds):

```bash
docker compose ps
```

All services should show `healthy` status.

### Access the Application

- **Frontend**: [http://localhost:8000](http://localhost:8000)
- **API Gateway**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Individual Services**: Check `docker-compose.yml` for port mappings

### Default Login Credentials

No default users are created. Register a new account via:
- **Patient**: [http://localhost:8000/register.html](http://localhost:8000/register.html)
- **Doctor**: [http://localhost:8000/register_doctor.html](http://localhost:8000/register_doctor.html)

### Stop Services

```bash
docker compose down
```

To remove volumes (⚠️ deletes all data):

```bash
docker compose down -v
```

---

## 💻 Development Guide

### Project Structure

```
telehealth/
├── api-gateway/              # API Gateway service
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── services/                 # Microservices
│   ├── admin/
│   ├── appointment/
│   ├── auth/
│   ├── bsp/
│   ├── chat/
│   ├── doctor/
│   ├── family/
│   ├── notification/
│   ├── patient/
│   ├── records/
│   └── sms/
├── wound_triage_api/        # Wound triage microservice
├── shared/                   # Shared utilities & models
│   ├── auth_utils.py
│   ├── database.py
│   ├── models.py
│   └── schemas.py
├── frontend/                 # Static frontend files
│   ├── index.html
│   ├── login.html
│   ├── patient_dashboard.html
│   ├── doctor_dashboard.html
│   └── assets/
├── docker-compose.yml       # Multi-container orchestration
├── .env.example             # Environment template
└── README.md                # This file
```

### Local Development Setup (Without Docker)

If you prefer to run services locally:

#### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies for each service
pip install -r services/auth/requirements.txt
# Repeat for other services
```

#### 2. Start Database Services

```bash
# Start PostgreSQL
docker run -d -p 5432:5432 \
  -e POSTGRES_USER=telehealth_user \
  -e POSTGRES_PASSWORD=telehealth_password \
  -e POSTGRES_DB=telehealth \
  postgres:15

# Start Redis
docker run -d -p 6379:6379 redis:latest

# Start MongoDB
docker run -d -p 27017:27017 mongo:7.0
```

#### 3. Update Environment Variables

For local development, change database hosts in `.env`:

```bash
DATABASE_URL=postgresql://telehealth_user:telehealth_password@localhost:5432/telehealth
REDIS_URL=redis://localhost:6379
```

#### 4. Run Individual Services

```bash
# Terminal 1 - Auth Service
cd services/auth
python main.py

# Terminal 2 - Patient Service
cd services/patient
python main.py

# ... repeat for other services
```

### Hot Reloading for Development

Services are configured with volume mounts in `docker-compose.yml` for hot reloading:

```yaml
volumes:
  - ./services/auth:/app
```

Changes to Python files will automatically reload the service.

### Adding a New Microservice

1. Create service directory in `services/`
2. Add `main.py`, `Dockerfile`, and `requirements.txt`
3. Update `docker-compose.yml` with new service
4. Update API Gateway routing in `api-gateway/main.py`
5. Rebuild: `docker compose build <service-name>`

### Database Migrations

The application uses SQLAlchemy with automatic table creation. To modify the schema:

1. Edit models in `shared/models.py`
2. Restart services to apply changes:
   ```bash
   docker compose restart auth-service patient-service doctor-service
   ```

For production, consider using [Alembic](https://alembic.sqlalchemy.org/) for migrations.

---

## 📚 API Documentation

### Comprehensive API Reference

We provide a **complete, interactive HTML documentation** covering all 12 microservices and 80+ endpoints:

**📄 [API_DOCUMENTATION.html](./API_DOCUMENTATION.html)** - Click to view on GitHub, then download to view locally

#### How to Access:

**Option 1: Download and View Locally** (Recommended)
1. Navigate to the repository on GitHub
2. Click on `API_DOCUMENTATION.html`
3. Click the "Download raw file" button (or right-click "Raw" → Save As)
4. Open the downloaded HTML file in your browser
5. Browse interactive documentation with:
   - Collapsible service sections
   - Search functionality
   - Request/response examples
   - Workflow diagrams

**Option 2: Clone Repository**
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
open API_DOCUMENTATION.html  # macOS
# or
xdg-open API_DOCUMENTATION.html  # Linux
# or simply double-click the file on Windows
```

#### What's Included:

- ✅ **All 12 Microservices** - Auth, Patient, Doctor, Appointment, Family, Chat, Records, Admin, Notification, Wound Triage (AI), SMS Gateway, BSP
- ✅ **80+ Endpoints** - Complete coverage of every API
- ✅ **Interactive Features** - Search, collapsible sections, syntax highlighting
- ✅ **Workflow Diagrams** - Visual Mermaid diagrams showing key user flows
- ✅ **Authentication Guide** - JWT token usage and examples
- ✅ **Request/Response Examples** - JSON examples for all endpoints
- ✅ **Error Handling** - HTTP status codes and error responses

### Interactive Swagger Docs (When Running)

Each service also exposes live Swagger/OpenAPI documentation when the application is running:

- **API Gateway**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Auth Service**: [http://localhost:8001/docs](http://localhost:8001/docs)
- **Patient Service**: [http://localhost:8002/docs](http://localhost:8002/docs)
- **Doctor Service**: [http://localhost:8003/docs](http://localhost:8003/docs)
- **Appointment Service**: [http://localhost:8004/docs](http://localhost:8004/docs)
- And so on for all services...

### Authentication

Most endpoints require JWT authentication. To authenticate:

1. **Login** to get a token:
   ```bash
   curl -X POST http://localhost:8000/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=user@example.com&password=yourpassword"
   ```

2. **Use the token** in subsequent requests:
   ```bash
   curl -X GET http://localhost:8000/patients/me \
     -H "Authorization: Bearer <your-access-token>"
   ```

### Quick Reference - Key Endpoints

#### Auth Service
- `POST /register/patient` - Register new patient
- `POST /register/doctor` - Register new doctor
- `POST /token` - Login and get JWT token
- `GET /user/me` - Get current user info

#### Appointment Service
- `GET /available-appointments` - Get available slots
- `POST /reserve_slot` - Reserve a time slot (5-min hold)
- `POST /confirm_slot` - Confirm appointment
- `GET /appointments` - List user appointments
- `POST /appointments/cancel/{id}` - Cancel appointment

#### Wound Triage Service (AI)
- `POST /triage/assess` - AI-powered symptom assessment
- `POST /triage/validate` - Doctor feedback for AI learning
- `POST /triage/clinical-support` - Get differential diagnosis
- `POST /triage/transcribe` - Hinglish voice-to-text

#### SMS Gateway
Supported SMS commands:
- `HELP` - List all commands
- `STATUS` - Check upcoming appointments
- `DOCTORS` - List available doctors
- `SLOTS <doctor_id> <date>` - Check available slots
- `BOOK <doctor_id> <date> <time>` - Book appointment
- `CANCEL <appointment_id>` - Cancel appointment

> **💡 Pro Tip:** For complete endpoint details, parameter descriptions, and response schemas, refer to the **[API_DOCUMENTATION.html](./API_DOCUMENTATION.html)** file.

---

## 🧪 Testing

### Run All Tests

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run tests with coverage
./run_tests.sh
```

### Test Individual Services

```bash
pytest services/auth/test_auth.py
pytest services/appointment/test_appointments.py
```

### API Testing

Use the provided test scripts:

```bash
# Test appointment booking flow
./test_appointments_api.sh

# Test health checks
./health_check.sh
```

### Load Testing

Test system performance:

```bash
python test_latency.py
```

---

## 🌐 Deployment

### Production Deployment Checklist

- [ ] Change `SECRET_KEY` to a strong, random value
- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Use managed database services (AWS RDS, Google Cloud SQL, etc.)
- [ ] Configure SSL/TLS certificates
- [ ] Set up monitoring (Prometheus, Grafana)
- [ ] Configure log aggregation (ELK stack, CloudWatch)
- [ ] Enable database backups
- [ ] Set up CI/CD pipeline
- [ ] Configure rate limiting
- [ ] Enable CORS for production domains

### Docker Deployment

Build production images:

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

### Kubernetes Deployment

(TODO: Add Kubernetes manifests)

### Cloud Platforms

The application can be deployed to:
- **AWS**: ECS, EKS, or EC2 with Docker Compose
- **Google Cloud**: GKE, Cloud Run
- **Azure**: AKS, Container Instances
- **Render.com**: Direct Docker Compose deployment

---

## 🐛 Troubleshooting

### Common Issues

#### Services Won't Start

**Problem**: `docker compose up` fails with port conflicts

**Solution**:
```bash
# Check what's using the port
lsof -i :8000

# Kill the process or change the port in docker-compose.yml
```

#### Database Connection Errors

**Problem**: `psycopg2.OperationalError: could not translate host name`

**Solution**:
- If running locally (not in Docker), change `DATABASE_URL` host from `postgres` to `localhost`
- Ensure PostgreSQL container is healthy: `docker compose ps`

#### Hot Reload Not Working

**Problem**: Code changes don't reflect in running container

**Solution**:
```bash
# Restart the specific service
docker compose restart <service-name>

# Or rebuild the image
docker compose up --build <service-name>
```

#### JWT Token Errors

**Problem**: `401 Unauthorized` or `Invalid token`

**Solution**:
- Ensure `SECRET_KEY` is consistent across all services
- Check token expiry (default: 30 minutes)
- Verify `Authorization: Bearer <token>` header format

### Logs

View logs for debugging:

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f auth-service

# Last 100 lines
docker compose logs --tail=100 appointment-service
```

### Database Access

Connect to PostgreSQL for debugging:

```bash
docker exec -it telehealth-postgres psql -U telehealth_user -d telehealth
```

Common queries:
```sql
-- List all users
SELECT id, name, email, role FROM users;

-- Check appointments
SELECT * FROM appointments WHERE status = 'CONFIRMED';

-- View slots
SELECT * FROM appointment_slots WHERE is_booked = false;
```

### Reset Database

⚠️ **Warning**: This deletes all data!

```bash
docker compose down -v
docker compose up -d
```

---

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

### Development Workflow

1. **Fork** the repository
2. **Create** a feature branch:
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Commit** your changes:
   ```bash
   git commit -m "Add amazing feature"
   ```
4. **Push** to your fork:
   ```bash
   git push origin feature/amazing-feature
   ```
5. **Open** a Pull Request

### Code Style

- Follow [PEP 8](https://pep8.org/) for Python code
- Use type hints where applicable
- Write docstrings for all functions/classes
- Keep functions small and focused

### Commit Messages

Use conventional commits:
- `feat: Add new appointment reminder feature`
- `fix: Resolve timezone issue in appointments`
- `docs: Update API documentation`
- `refactor: Simplify auth logic`
- `test: Add unit tests for patient service`

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **FastAPI** - Modern web framework for building APIs
- **Docker** - Containerization platform
- **PostgreSQL** - Primary database
- **Redis** - Caching and queue management
- **MongoDB** - Document store for triage data

---

## 📞 Support

For questions or issues:
- **GitHub Issues**: Report bugs or request features
- **Discussions**: Ask questions in GitHub Discussions
- **Email**: [support@healthconnect.example.com](mailto:support@healthconnect.example.com)

---

<div align="center">

**Built with ❤️ for accessible healthcare**

[⬆ Back to Top](#healthconnect-telehealth-platform)

</div>
