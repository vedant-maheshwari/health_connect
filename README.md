# Telehealth Microservices Architecture

A microservices-based telehealth application built with FastAPI, featuring user management, appointments, doctor-patient interactions, family connections, and real-time chat.

## 🏗️ Architecture Overview

This application is decomposed into 7 independent microservices:

```
┌─────────────────┐
│   API Gateway   │ :8000
│   (Frontend)    │
└────────┬────────┘
         │
    ┌────┴───────────────────────┐
    │                            │
┌───▼──────┐  ┌──────────┐  ┌──▼─────────┐
│  Auth    │  │ Patient  │  │  Doctor    │
│ Service  │  │ Service  │  │  Service   │
│  :8001   │  │  :8002   │  │   :8003    │
└──────────┘  └────┬─────┘  └────────────┘
                   │
        ┌──────────┼────────────┬─────────┐
        │          │            │         │
  ┌─────▼──┐  ┌───▼────┐  ┌───▼─────┐ ┌─▼────┐
  │Appoint │  │Family  │  │  Chat   │ │Admin │
  │ment    │  │Service │  │ Service │ │Service│
  │ :8004  │  │ :8005  │  │  :8006  │ │ :8007│
  └────────┘  └────────┘  └─────────┘ └──────┘
       │
  ┌────▼─────┐
  │  Redis   │
  │  :6379   │
  └──────────┘
       │
  ┌────▼─────────┐
  │  PostgreSQL  │
  │    :5432     │
  └──────────────┘
```

## 📦 Services

### 1. **Auth Service** (Port 8001)
- User registration (patient, doctor, family)
- JWT token generation and validation
- User authentication

### 2. **Patient Service** (Port 8002)
- Patient profile management
- Patient vitals viewing
- Appointment history

### 3. **Doctor Service** (Port 8003)
- Doctor profile management
- Availability management
- Patient vitals recording

### 4. **Appointment Service** (Port 8004)
- Appointment booking
- Redis-based slot reservation (5-min TTL)
- WebSocket for real-time updates
- Appointment status management

### 5. **Family Service** (Port 8005)
- Family connections
- Invitations
- Permissions management

### 6. **Chat Service** (Port 8006)
- Chat rooms
- Real-time messaging
- Chat authentication

### 7. **Admin Service** (Port 8007)
- Admin dashboard
- System logging
- User management

### 8. **API Gateway** (Port 8000)
- Routes requests to services
- JWT validation
- Serves frontend static files

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### Running with Docker Compose

1. **Clone and navigate to microservices directory:**
```bash
cd microservices
```

2. **Configure environment variables:**
```bash
# Edit .env file with your configuration
# SECRET_KEY is already set, but you should change it in production
```

3. **Start all services:**
```bash
docker-compose up --build
```

This will start:
- PostgreSQL (port 5432)
- Redis (port 6379)
- All 7 microservices (ports 8001-8007)
- API Gateway (port 8000)

4. **Access the application:**
- Frontend: http://localhost:8000/frontend/
- API Gateway: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Running Individual Services (Development)

Each service can be run independently:

```bash
cd services/auth
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost:5432/telehealth"
export SECRET_KEY="your-secret-key"

# Run the service
python main.py
```

## 🔧 Configuration

### Environment Variables

Key environment variables (in `.env` file):

```env
DATABASE_URL=postgresql://telehealth_user:telehealth_password@postgres:5432/telehealth
REDIS_URL=redis://redis:6379
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Service URLs

Services communicate via these URLs (configured in docker-compose.yml):
- `http://auth-service:8000`
- `http://patient-service:8000`
- `http://doctor-service:8000`
- etc.

## 📡 API Endpoints

### Authentication
- `POST /register/patient` - Register patient
- `POST /register/doctor` - Register doctor
- `POST /register/family` - Register family member
- `POST /token` - Login (get JWT token)
- `GET /user/me` - Get current user

### Doctors
- `GET /all_doctors` - List all doctors
- `PUT /doctors/me/availability` - Update availability
- `GET /doctors/me/availability` - Get availability
- `POST /vitals` - Add patient vitals

### Patients
- `GET /patients/me` - Get patient profile
- `GET /patients/me/vitals` - Get patient vitals
- `GET /patient/appointments/detailed` - Get appointments

### Appointments
- `GET /available_appointment?doctor_id=X&app_date=YYYY-MM-DD` - Get available slots
- `POST /reserve_slot` - Reserve a slot (5 minutes)
- `POST /confirm_slot` - Confirm reservation
- `WS /ws/doctor/{doctor_id}/slots` - Real-time slot updates

## 🧪 Testing

### Health Checks

Check if all services are running:

```bash
# Gateway
curl http://localhost:8000/health

# Auth Service
curl http://localhost:8001/health

# Patient Service
curl http://localhost:8002/health

# And so on for other services...
```

### End-to-End Test

```bash
# 1. Register a patient
curl -X POST http://localhost:8000/register/patient \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Patient","email":"test@example.com","password":"test123","date_of_birth":"2000-01-01"}'

# 2. Login
curl -X POST http://localhost:8000/token \
  -d "username=test@example.com&password=test123"

# 3. Use the returned token for authenticated requests
```

## 🗄️ Database

### Schema
All services share the same PostgreSQL database but could be migrated to separate databases in the future.

### Migrations
Database tables are auto-created on service startup using SQLAlchemy's `Base.metadata.create_all()`.

For production, consider using Alembic for migrations.

## 📊 Monitoring & Logging

- Health check endpoints: `/health` on each service
- Admin service provides centralized logging
- Docker logs: `docker-compose logs -f [service-name]`

## 🔐 Security

- JWT-based authentication
- Password hashing with bcrypt
- CORS configured in API Gateway
- Environment-based secrets

## 🛠️ Development

### Adding a New Service

1. Create service directory: `services/new-service/`
2. Create `main.py` with FastAPI app
3. Create `Dockerfile`
4. Add service to `docker-compose.yml`
5. Add routes to API Gateway

### Project Structure

```
microservices/
├── shared/              # Shared code
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   └── auth_utils.py
├── services/
│   ├── auth/
│   ├── patient/
│   ├── doctor/
│   ├── appointment/
│   ├── family/
│   ├── chat/
│   └── admin/
├── api-gateway/
├── docker-compose.yml
├── .env
└── README.md
```

## 🚢 Deployment

### Docker Compose (Recommended for small-scale)

```bash
docker-compose up -d --build
```

### Kubernetes (For production)

1. Build and push images to registry
2. Create Kubernetes deployment files
3. Apply configurations:
```bash
kubectl apply -f k8s/
```

### Individual Containers

Each service can be deployed independently:
```bash
docker build -t auth-service -f services/auth/Dockerfile .
docker run -p 8001:8000 auth-service
```

## 🐛 Troubleshooting

### Service won't start
- Check logs: `docker-compose logs [service-name]`
- Verify environment variables
- Ensure PostgreSQL and Redis are running

### Cannot connect to database
- Verify DATABASE_URL in .env
- Check PostgreSQL container: `docker-compose ps postgres`
- Check network: `docker network ls`

### Redis connection issues
- Ensure Redis is running: `docker-compose ps redis`
- Verify REDIS_URL in appointment service

## 📝 Migration from Monolith

This microservices architecture maintains API compatibility with the original monolithic application:

1. All endpoints remain the same (via API Gateway)
2. Database schema unchanged
3. Frontend requires no modifications
4. JWT tokens work identically

### Differences
- Services run on separate ports (8001-8007)
- Inter-service communication via HTTP
- Redis required for appointment service
- Slightly increased latency due to gateway routing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with Docker Compose
5. Submit a pull request

## 📄 License

[Your License Here]

## 🆘 Support

For issues or questions, please open an issue on GitHub.

---

**Built with FastAPI, PostgreSQL, Redis, and Docker** 🚀
