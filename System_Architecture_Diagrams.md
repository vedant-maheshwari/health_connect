# Telehealth System - Architecture & UML Diagrams

## 1. System Architecture Overview

The telehealth system is built using a **microservices architecture** with the following key components:

```mermaid
graph TB
    subgraph "Client Layer"
        WEB["Web Browser"]
        MOBILE["Mobile App<br/>(Future)"]
    end

    subgraph "Frontend Applications"
        DOCTOR_UI["Doctor Dashboard<br/>doctor_dashboard.html"]
        PATIENT_UI["Patient Dashboard<br/>patient_dashboard.html"]
        LOGIN["Login/Register<br/>login.html"]
    end

    subgraph "API Gateway Layer"
        GATEWAY["API Gateway<br/>:8000<br/>Route Management<br/>Load Balancing"]
    end

    subgraph "Microservices Layer"
        AUTH["Auth Service<br/>:8001<br/>JWT Authentication"]
        DOCTOR["Doctor Service<br/>:8002<br/>Doctor Management"]
        PATIENT["Patient Service<br/>:8003<br/>Patient Management"]
        APPT["Appointment Service<br/>:8004<br/>Scheduling & Queue"]
        TRIAGE["Triage Service<br/>:8005<br/>AI Diagnosis<br/>LLM + RAG"]
        BSP["BSP Service<br/>:8006<br/>Signal Processing<br/>AFib Detection"]
        WOUND["Wound Triage<br/>:8007<br/>Image Analysis"]
        CHAT["Chat Service<br/>:8008<br/>WebSocket"]
        RECORDS["Records Service<br/>:8009<br/>Medical Records"]
        FAMILY["Family Service<br/>:8010<br/>Family Links"]
        NOTIF["Notification Service<br/>:8011<br/>Email/SMS"]
        SMS["SMS Service<br/>:8012<br/>Twilio Integration"]
        ADMIN["Admin Service<br/>:8013<br/>Analytics"]
    end

    subgraph "Data Layer"
        DB[(PostgreSQL<br/>Database<br/>:5432)]
        REDIS[("Redis Cache<br/>(Future)")]
    end

    subgraph "External Services"
        LLM_API["LLM API<br/>AI Analysis"]
        COHERE["Cohere API<br/>Embeddings"]
        SARVAM["Sarvam AI<br/>Speech-to-Text"]
        TWILIO["Twilio<br/>SMS Gateway"]
    end

    WEB --> DOCTOR_UI
    WEB --> PATIENT_UI
    WEB --> LOGIN

    DOCTOR_UI --> GATEWAY
    PATIENT_UI --> GATEWAY
    LOGIN --> GATEWAY

    GATEWAY --> AUTH
    GATEWAY --> DOCTOR
    GATEWAY --> PATIENT
    GATEWAY --> APPT
    GATEWAY --> TRIAGE
    GATEWAY --> BSP
    GATEWAY --> WOUND
    GATEWAY --> CHAT
    GATEWAY --> RECORDS
    GATEWAY --> FAMILY
    GATEWAY --> NOTIF
    GATEWAY --> SMS
    GATEWAY --> ADMIN

    AUTH --> DB
    DOCTOR --> DB
    PATIENT --> DB
    APPT --> DB
    RECORDS --> DB
    FAMILY --> DB
    CHAT --> DB

    TRIAGE --> LLM_API
    TRIAGE --> COHERE
    TRIAGE --> SARVAM
    TRIAGE --> DB

    SMS --> TWILIO
    NOTIF --> TWILIO

    style GATEWAY fill:#4285f4,color:#fff
    style DB fill:#336791,color:#fff
    style LLM_API fill:#ea4335,color:#fff
    style COHERE fill:#ff6b6b,color:#fff
```

---

## 2. User Flow Diagrams

### 2.1 Patient Journey - Booking Appointment

```mermaid
flowchart TD
    START([Patient Logs In]) --> SEARCH[Search for Doctor]
    SEARCH --> VIEW[View Doctor Profile<br/>& Availability]
    VIEW --> SELECT[Select Time Slot]
    SELECT --> RESERVE[Reserve Slot<br/>15 min hold]
    RESERVE --> CONFIRM{Confirm<br/>Appointment?}
    CONFIRM -->|Yes| PAYMENT[Payment<br/>Processing]
    CONFIRM -->|No| CANCEL[Slot Released]
    PAYMENT --> BOOKED[Appointment Booked]
    BOOKED --> NOTIF[SMS/Email<br/>Confirmation]
    NOTIF --> WAIT[Wait for<br/>Appointment Day]
    WAIT --> CHECKIN[Check-In via<br/>Patient Dashboard]
    CHECKIN --> QUEUE[Added to<br/>Doctor's Queue]
    QUEUE --> CONSULT[Live Consultation<br/>with Doctor]
    CONSULT --> END([Consultation Complete])

    style START fill:#4CAF50,color:#fff
    style BOOKED fill:#2196F3,color:#fff
    style CONSULT fill:#9C27B0,color:#fff
    style END fill:#4CAF50,color:#fff
```

### 2.2 Doctor Journey - Daily Workflow

```mermaid
flowchart TD
    START([Doctor Logs In]) --> DASH[View Dashboard]
    DASH --> STARTDAY{Start My Day<br/>Button}
    STARTDAY --> QUEUE[Auto-Queue<br/>Today's Appointments]
    QUEUE --> VIEW[View Patient Queue]
    VIEW --> NEXT{Call Next<br/>Patient?}
    NEXT --> CONSULT[Start Live<br/>Consultation]
    CONSULT --> RECORD[Record Audio]
    RECORD --> TRANSCRIBE[Sarvam AI<br/>Speech-to-Text]
    TRANSCRIBE --> AI[LLM<br/>Analysis]
    AI --> SOAP[Generate SOAP<br/>Notes]
    SOAP --> EDIT[Doctor Edits<br/>Notes]
    EDIT --> SAVE[Save to Patient<br/>Record]
    SAVE --> COMPLETE[Mark Complete<br/>Remove from Queue]
    COMPLETE --> MORE{More<br/>Patients?}
    MORE -->|Yes| NEXT
    MORE -->|No| END([End of Day])

    style START fill:#4CAF50,color:#fff
    style CONSULT fill:#9C27B0,color:#fff
    style AI fill:#FF9800,color:#fff
    style SAVE fill:#2196F3,color:#fff
    style END fill:#4CAF50,color:#fff
```

### 2.3 AI Triage Flow with Feedback Learning

```mermaid
flowchart TD
    START([Patient Submits<br/>Symptoms]) --> LANG{Language<br/>Detection}
    LANG -->|Hindi/Hinglish| TRANS[Sarvam AI<br/>Translation]
    LANG -->|English| PROC
    TRANS --> PROC[Process Input]
    PROC --> EMB[Cohere<br/>Embeddings]
    EMB --> RAG[Vector Search<br/>Similar Cases]
    RAG --> LLM_ANALYSIS[LLM<br/>Analysis]
    LLM_ANALYSIS --> DIAG[Differential<br/>Diagnosis]
    LLM_ANALYSIS --> TREAT[Treatment<br/>Recommendations]
    LLM_ANALYSIS --> LABS[Lab Tests<br/>Suggested]
    LLM_ANALYSIS --> URGENCY[Urgency Level]
    DIAG --> DISPLAY
    TREAT --> DISPLAY
    LABS --> DISPLAY
    URGENCY --> DISPLAY[Display Results<br/>to Patient]
    
    DISPLAY --> WAIT[Patient waits for<br/>Doctor Appointment]
    WAIT --> DOC_CONSULT[Doctor Consultation]
    DOC_CONSULT --> DOC_DIAG[Doctor's Actual<br/>Diagnosis]
    DOC_DIAG --> FEEDBACK{Doctor Provides<br/>Feedback?}
    
    FEEDBACK -->|Yes| COMPARE[LLM Compares:<br/>AI Prediction vs<br/>Doctor Feedback]
    FEEDBACK -->|No| END
    
    COMPARE --> ANALYZE[LLM Analyzes<br/>Discrepancies]
    ANALYZE --> EXTRACT[Extract Learning<br/>Context & Patterns]
    EXTRACT --> SAVE_FEEDBACK[Save to Feedback<br/>Table in DB]
    SAVE_FEEDBACK --> UPDATE_RAG[Update RAG<br/>Vector Database]
    UPDATE_RAG --> IMPROVE[System Learns &<br/>Improves]
    IMPROVE --> END([End])

    style START fill:#4CAF50,color:#fff
    style LLM_ANALYSIS fill:#FF9800,color:#fff
    style COMPARE fill:#9C27B0,color:#fff
    style UPDATE_RAG fill:#2196F3,color:#fff
    style IMPROVE fill:#4CAF50,color:#fff
    style END fill:#4CAF50,color:#fff
```

**Feedback Learning Process:**
1. **Initial AI Diagnosis**: LLM analyzes symptoms and provides recommendations
2. **Doctor Validation**: Real doctor examines patient and provides actual diagnosis
3. **LLM Comparison**: Another LLM call compares AI prediction with doctor feedback
4. **Context Extraction**: System identifies what was correct, what was wrong, and why
5. **Database Update**: Saves feedback with learning context to `feedback` table
6. **RAG Enhancement**: Updates vector embeddings with new knowledge for future queries

---

## 3. Software Architecture Diagrams

### 3.1 Layered Architecture

```mermaid
graph TB
    subgraph "Presentation Layer"
        UI1[Doctor Dashboard]
        UI2[Patient Dashboard]
        UI3[Login UI]
    end

    subgraph "API Layer"
        GW[API Gateway<br/>FastAPI]
        MIDDLEWARE[Middleware Layer]
        AUTH_MW[Authentication]
        CORS_MW[CORS Handler]
        LOGGING[Logging & Monitoring]
    end

    subgraph "Business Logic Layer"
        subgraph "Core Services"
            AUTH_BL[Authentication Logic]
            APPT_BL[Appointment Logic]
            QUEUE_BL[Queue Management]
            DOC_BL[Doctor Logic]
            PAT_BL[Patient Logic]
        end
        
        subgraph "AI Services"
            TRIAGE_BL[Triage Logic<br/>RAG System]
            BSP_BL[Signal Processing]
            WOUND_BL[Image Analysis]
            FEEDBACK_BL[Feedback Learning]
        end
        
        subgraph "Communication Services"
            CHAT_BL[Chat Logic<br/>WebSocket]
            NOTIF_BL[Notification Logic]
            SMS_BL[SMS Logic]
        end
    end

    subgraph "Data Access Layer"
        ORM[SQLAlchemy ORM]
        MODELS[Data Models]
        MIGRATIONS[Alembic Migrations]
    end

    subgraph "Data Layer"
        POSTGRES[(PostgreSQL<br/>Relational Data)]
        VECTOR[(ChromaDB<br/>Vector Store)]
        CACHE[(Redis Cache<br/>Future)]
    end

    subgraph "External Integration Layer"
        LLM_INT[LLM API Client]
        COHERE_INT[Cohere Client]
        SARVAM_INT[Sarvam Client]
        TWILIO_INT[Twilio Client]
    end

    UI1 --> GW
    UI2 --> GW
    UI3 --> GW
    
    GW --> MIDDLEWARE
    MIDDLEWARE --> AUTH_MW
    MIDDLEWARE --> CORS_MW
    MIDDLEWARE --> LOGGING
    
    AUTH_MW --> AUTH_BL
    GW --> APPT_BL
    GW --> DOC_BL
    GW --> PAT_BL
    GW --> TRIAGE_BL
    GW --> CHAT_BL
    
    AUTH_BL --> ORM
    APPT_BL --> ORM
    QUEUE_BL --> ORM
    DOC_BL --> ORM
    PAT_BL --> ORM
    CHAT_BL --> ORM
    
    TRIAGE_BL --> LLM_INT
    TRIAGE_BL --> COHERE_INT
    TRIAGE_BL --> SARVAM_INT
    TRIAGE_BL --> ORM
    TRIAGE_BL --> VECTOR
    
    FEEDBACK_BL --> LLM_INT
    FEEDBACK_BL --> ORM
    FEEDBACK_BL --> VECTOR
    
    SMS_BL --> TWILIO_INT
    NOTIF_BL --> TWILIO_INT
    
    ORM --> MODELS
    ORM --> POSTGRES
    
    style GW fill:#4285f4,color:#fff
    style POSTGRES fill:#336791,color:#fff
    style VECTOR fill:#9C27B0,color:#fff
```

### 3.2 Microservice Internal Structure

```mermaid
graph TB
    subgraph "Triage Service (Port 8005)"
        TRIAGE_API[FastAPI Router<br/>/triage/*]
        
        subgraph "Endpoints"
            EP1[POST /analyze]
            EP2[POST /clinical-support]
            EP3[POST /transcribe]
            EP4[POST /feedback]
        end
        
        subgraph "Business Logic"
            SYMPTOM_ANALYZER[Symptom Analyzer]
            CLINICAL_SUPPORT[Clinical Support Engine]
            TRANSCRIPTION[Audio Transcription]
            FEEDBACK_PROCESSOR[Feedback Processor]
        end
        
        subgraph "AI Integration"
            LLM_CLIENT[LLM Client]
            EMBEDDING_CLIENT[Cohere Embeddings]
            STT_CLIENT[Sarvam STT]
        end
        
        subgraph "Data Layer"
            VECTOR_DB[ChromaDB<br/>Vector Store]
            FEEDBACK_DB[PostgreSQL<br/>Feedback Table]
            RAG_ENGINE[RAG Engine]
        end
        
        TRIAGE_API --> EP1
        TRIAGE_API --> EP2
        TRIAGE_API --> EP3
        TRIAGE_API --> EP4
        
        EP1 --> SYMPTOM_ANALYZER
        EP2 --> CLINICAL_SUPPORT
        EP3 --> TRANSCRIPTION
        EP4 --> FEEDBACK_PROCESSOR
        
        SYMPTOM_ANALYZER --> EMBEDDING_CLIENT
        SYMPTOM_ANALYZER --> RAG_ENGINE
        SYMPTOM_ANALYZER --> LLM_CLIENT
        
        CLINICAL_SUPPORT --> LLM_CLIENT
        TRANSCRIPTION --> STT_CLIENT
        
        FEEDBACK_PROCESSOR --> LLM_CLIENT
        FEEDBACK_PROCESSOR --> FEEDBACK_DB
        FEEDBACK_PROCESSOR --> RAG_ENGINE
        
        RAG_ENGINE --> VECTOR_DB
        RAG_ENGINE --> EMBEDDING_CLIENT
    end
    
    style TRIAGE_API fill:#4285f4,color:#fff
    style LLM_CLIENT fill:#FF9800,color:#fff
    style VECTOR_DB fill:#9C27B0,color:#fff
```

### 3.3 API Request Flow Pattern

```mermaid
sequenceDiagram
    participant Client
    participant Gateway as API Gateway
    participant Auth as Auth Middleware
    participant Service as Microservice
    participant BL as Business Logic
    participant DAL as Data Access
    participant DB as Database
    participant External as External API

    Client->>Gateway: HTTP Request
    Gateway->>Auth: Validate JWT Token
    
    alt Token Invalid
        Auth-->>Gateway: 401 Unauthorized
        Gateway-->>Client: Error Response
    else Token Valid
        Auth-->>Gateway: User Context
        Gateway->>Service: Forward Request + Context
        Service->>BL: Execute Business Logic
        
        alt Needs External API
            BL->>External: API Call
            External-->>BL: Response
        end
        
        BL->>DAL: Database Operation
        DAL->>DB: SQL Query
        DB-->>DAL: Result
        DAL-->>BL: Mapped Objects
        BL-->>Service: Process Result
        Service-->>Gateway: JSON Response
        Gateway-->>Client: HTTP Response
    end
```

### 3.4 Data Flow Architecture

```mermaid
graph LR
    subgraph "Input Sources"
        WEB[Web UI]
        API_REQ[API Requests]
        WS[WebSocket]
    end

    subgraph "API Gateway"
        ROUTER[Request Router]
        VALIDATOR[Input Validator]
        TRANSFORMER[Data Transformer]
    end

    subgraph "Service Layer"
        SERVICES[Microservices]
    end

    subgraph "Processing"
        BUSINESS[Business Rules]
        AI[AI Processing]
        VALIDATION[Data Validation]
    end

    subgraph "Storage"
        WRITE[Write Operations]
        READ[Read Operations]
        CACHE_OPS[Cache Operations]
    end

    subgraph "Persistence"
        DB[(Database)]
        VECTOR[(Vector DB)]
        FILES[File Storage]
    end

    subgraph "Output"
        RESPONSE[API Response]
        NOTIFICATION[Notifications]
        EVENTS[System Events]
    end

    WEB --> ROUTER
    API_REQ --> ROUTER
    WS --> ROUTER
    
    ROUTER --> VALIDATOR
    VALIDATOR --> TRANSFORMER
    TRANSFORMER --> SERVICES
    
    SERVICES --> BUSINESS
    SERVICES --> AI
    BUSINESS --> VALIDATION
    
    VALIDATION --> WRITE
    VALIDATION --> READ
    
    WRITE --> DB
    WRITE --> VECTOR
    AI --> VECTOR
    READ --> DB
    READ --> VECTOR
    
    DB --> RESPONSE
    VECTOR --> RESPONSE
    
    RESPONSE --> WEB
    SERVICES --> NOTIFICATION
    SERVICES --> EVENTS

    style ROUTER fill:#4285f4,color:#fff
    style AI fill:#FF9800,color:#fff
    style DB fill:#336791,color:#fff
    style VECTOR fill:#9C27B0,color:#fff
```

### 3.5 Authentication & Authorization Flow

```mermaid
graph TB
    START([User Login Request]) --> SUBMIT[Submit Credentials<br/>Email + Password]
    SUBMIT --> AUTH_SVC[Auth Service]
    AUTH_SVC --> HASH_CHECK{Password Hash<br/>Match?}
    
    HASH_CHECK -->|No| FAIL[Return 401<br/>Unauthorized]
    HASH_CHECK -->|Yes| GENERATE[Generate JWT Token]
    
    GENERATE --> PAYLOAD[Token Payload:<br/>user_id, role, exp]
    PAYLOAD --> SIGN[Sign with Secret Key]
    SIGN --> RETURN_TOKEN[Return Token to Client]
    RETURN_TOKEN --> STORE[Client Stores<br/>in localStorage]
    
    STORE --> FUTURE_REQ[Future API Request]
    FUTURE_REQ --> HEADER[Include Token in<br/>Authorization Header]
    HEADER --> GATEWAY[API Gateway]
    GATEWAY --> VERIFY{Verify Token<br/>Signature}
    
    VERIFY -->|Invalid| REJECT[403 Forbidden]
    VERIFY -->|Valid| DECODE[Decode Payload]
    DECODE --> CHECK_EXP{Token<br/>Expired?}
    
    CHECK_EXP -->|Yes| REFRESH[Refresh Token Flow]
    CHECK_EXP -->|No| EXTRACT[Extract User Context]
    EXTRACT --> AUTHORIZE{Role<br/>Authorized?}
    
    AUTHORIZE -->|No| FORBIDDEN[403 Forbidden]
    AUTHORIZE -->|Yes| PROCEED[Proceed to Service]
    
    PROCEED --> END([Request Processed])
    
    style AUTH_SVC fill:#4285f4,color:#fff
    style GENERATE fill:#2196F3,color:#fff
    style PROCEED fill:#4CAF50,color:#fff
```

---

## 4. Component Diagram (UML)

```mermaid
graph TB
    subgraph "Frontend Components"
        DC["Doctor Dashboard<br/>Component"]
        PC["Patient Dashboard<br/>Component"]
        LC["Login Component"]
        BSP_UI["BSP Toolkit UI<br/>Tool Library"]
    end

    subgraph "API Gateway"
        ROUTER["Route Manager"]
        AUTH_MW["Auth Middleware"]
        CORS["CORS Handler"]
    end

    subgraph "Core Services"
        AUTH_SVC["Authentication Service<br/>- register()<br/>- login()<br/>- verify_token()"]
        DOC_SVC["Doctor Service<br/>- get_profile()<br/>- set_availability()<br/>- get_patients()"]
        PAT_SVC["Patient Service<br/>- get_profile()<br/>- update_vitals()<br/>- get_records()"]
        APPT_SVC["Appointment Service<br/>- reserve_slot()<br/>- confirm_booking()<br/>- start_day_queue()<br/>- manage_queue()"]
    end

    subgraph "AI Services"
        TRIAGE_SVC["Triage Service<br/>- analyze_symptoms()<br/>- clinical_support()<br/>- transcribe_audio()"]
        BSP_SVC["BSP Service<br/>- process_signals()<br/>- detect_afib()"]
        WOUND_SVC["Wound Service<br/>- analyze_image()<br/>- classify_wound()"]
    end

    subgraph "Communication Services"
        CHAT_SVC["Chat Service<br/>- WebSocket Handler<br/>- message_history()"]
        NOTIF_SVC["Notification Service<br/>- send_email()<br/>- send_sms()"]
    end

    subgraph "Data Models"
        USER_MODEL["User Model<br/>- id<br/>- email<br/>- role"]
        APPT_MODEL["Appointment Model<br/>- id<br/>- doctor_id<br/>- patient_id<br/>- datetime"]
        QUEUE_MODEL["Queue Model<br/>- position<br/>- status<br/>- waiting_time"]
        RECORD_MODEL["Medical Record<br/>- soap_notes<br/>- vitals<br/>- history"]
    end

    DC --> ROUTER
    PC --> ROUTER
    LC --> ROUTER
    BSP_UI --> ROUTER

    ROUTER --> AUTH_MW
    AUTH_MW --> AUTH_SVC
    ROUTER --> DOC_SVC
    ROUTER --> PAT_SVC
    ROUTER --> APPT_SVC
    ROUTER --> TRIAGE_SVC
    ROUTER --> BSP_SVC
    ROUTER --> CHAT_SVC

    DOC_SVC --> USER_MODEL
    PAT_SVC --> USER_MODEL
    APPT_SVC --> APPT_MODEL
    APPT_SVC --> QUEUE_MODEL
    TRIAGE_SVC --> RECORD_MODEL

    style ROUTER fill:#4285f4,color:#fff
    style TRIAGE_SVC fill:#FF9800,color:#fff
    style BSP_SVC fill:#9C27B0,color:#fff
```

---

## 4. Database Entity Relationship Diagram

```mermaid
erDiagram
    USERS ||--o{ DOCTORS : "is_a"
    USERS ||--o{ PATIENTS : "is_a"
    DOCTORS ||--o{ APPOINTMENTS : "has"
    PATIENTS ||--o{ APPOINTMENTS : "books"
    DOCTORS ||--o{ AVAILABILITY : "sets"
    DOCTORS ||--o{ DOCTOR_PATIENTS : "treats"
    PATIENTS ||--o{ DOCTOR_PATIENTS : "assigned_to"
    PATIENTS ||--o{ MEDICAL_RECORDS : "has"
    DOCTORS ||--o{ MEDICAL_RECORDS : "creates"
    APPOINTMENTS ||--o{ APPOINTMENT_QUEUE : "in_queue"
    PATIENTS ||--o{ CHAT_MESSAGES : "sends"
    DOCTORS ||--o{ CHAT_MESSAGES : "sends"
    PATIENTS ||--o{ FAMILY_LINKS : "member_of"
    PATIENTS ||--o{ FEEDBACK : "provides"

    USERS {
        int id PK
        string email UK
        string password_hash
        string role
        datetime created_at
    }

    DOCTORS {
        int id PK
        int user_id FK
        string name
        string specialty
        string qualification
        int experience
        float consultation_fee
    }

    PATIENTS {
        int id PK
        int user_id FK
        string name
        string phone
        date date_of_birth
        string gender
        json medical_history
    }

    APPOINTMENTS {
        int id PK
        int doctor_id FK
        int patient_id FK
        datetime appointment_time
        int duration
        string status
        float amount
    }

    AVAILABILITY {
        int id PK
        int doctor_id FK
        int day_of_week
        time start_time
        time end_time
        int appointment_duration
        time break_start
        time break_end
    }

    APPOINTMENT_QUEUE {
        int id PK
        int appointment_id FK
        int doctor_id FK
        int patient_id FK
        datetime check_in_time
        string status
        int position
    }

    MEDICAL_RECORDS {
        int id PK
        int patient_id FK
        int doctor_id FK
        datetime consultation_date
        text chief_complaint
        text subjective
        text objective
        text assessment
        text plan
    }

    DOCTOR_PATIENTS {
        int id PK
        int doctor_id FK
        int patient_id FK
        datetime assigned_at
    }

    CHAT_MESSAGES {
        int id PK
        int sender_id FK
        int receiver_id FK
        text message
        datetime timestamp
        boolean is_read
    }

    FAMILY_LINKS {
        int id PK
        int patient_id FK
        int family_member_id FK
        string relationship
        string status
    }

    FEEDBACK {
        int id PK
        int patient_id FK
        text symptoms_input
        text ai_diagnosis
        text doctor_feedback
        boolean was_correct
        datetime created_at
    }
```

---

## 5. Class Diagram - Core Models

```mermaid
classDiagram
    class User {
        +int id
        +string email
        +string password_hash
        +UserRole role
        +datetime created_at
        +verify_password(password)
        +generate_token()
    }

    class Doctor {
        +int id
        +User user
        +string name
        +string specialty
        +string qualification
        +int experience
        +float consultation_fee
        +set_availability(schedule)
        +get_appointments()
        +get_queue()
    }

    class Patient {
        +int id
        +User user
        +string name
        +string phone
        +date dob
        +Gender gender
        +dict medical_history
        +book_appointment(doctor, time)
        +check_in()
        +get_records()
    }

    class Appointment {
        +int id
        +Doctor doctor
        +Patient patient
        +datetime appointment_time
        +int duration
        +AppointmentStatus status
        +float amount
        +reserve()
        +confirm()
        +cancel()
    }

    class AppointmentQueue {
        +int id
        +Appointment appointment
        +QueueStatus status
        +int position
        +datetime check_in_time
        +int waiting_minutes
        +move_to_in_progress()
        +mark_completed()
        +remove_from_queue()
    }

    class MedicalRecord {
        +int id
        +Patient patient
        +Doctor doctor
        +datetime consultation_date
        +string chief_complaint
        +SOAPNote soap_note
        +save()
        +get_history()
    }

    class SOAPNote {
        +string subjective
        +string objective
        +string assessment
        +string plan
        +to_json()
    }

    class TriageService {
        -LLMClient ai_client
        -CohereClient embeddings
        -ChromaDB vector_db
        +analyze_symptoms(symptoms, history)
        +clinical_support(patient_data)
        +transcribe_audio(audio_file)
        -similarity_search(symptoms)
    }

    class BSPService {
        -TensorFlowModel afib_model
        +analyze_signals(header, data)
        +detect_afib(ecg, ppg)
        -preprocess_signals(raw_data)
    }

    User <|-- Doctor : extends
    User <|-- Patient : extends
    Doctor "1" --* "many" Appointment
    Patient "1" --* "many" Appointment
    Appointment "1" --o "0..1" AppointmentQueue
    Doctor "1" --* "many" MedicalRecord
    Patient "1" --* "many" MedicalRecord
    MedicalRecord *-- SOAPNote

    class UserRole {
        <<enumeration>>
        DOCTOR
        PATIENT
        ADMIN
    }

    class AppointmentStatus {
        <<enumeration>>
        RESERVED
        CONFIRMED
        COMPLETED
        CANCELLED
    }

    class QueueStatus {
        <<enumeration>>
        WAITING
        IN_PROGRESS
        COMPLETED
        DELAYED
        NO_SHOW
        REMOVED
    }
```

---

## 6. Sequence Diagram - Appointment Booking

```mermaid
sequenceDiagram
    actor Patient
    participant UI as Patient Dashboard
    participant Gateway as API Gateway
    participant Auth as Auth Service
    participant Appt as Appointment Service
    participant DB as Database
    participant SMS as SMS Service

    Patient->>UI: Search for doctor
    UI->>Gateway: GET /doctors/search
    Gateway->>Auth: Verify token
    Auth-->>Gateway: Token valid
    Gateway->>DB: Query doctors
    DB-->>Gateway: Doctor list
    Gateway-->>UI: Return doctors
    UI-->>Patient: Display results

    Patient->>UI: Select time slot
    UI->>Gateway: POST /appointments/reserve
    Gateway->>Auth: Verify token
    Auth-->>Gateway: Token valid
    Gateway->>Appt: Reserve slot
    Appt->>DB: Check availability
    DB-->>Appt: Slot available
    Appt->>DB: Create reservation (15 min hold)
    DB-->>Appt: Reservation created
    Appt-->>Gateway: Slot reserved
    Gateway-->>UI: Confirmation
    UI-->>Patient: "Reserved for 15 minutes"

    Patient->>UI: Confirm booking
    UI->>Gateway: POST /appointments/confirm
    Gateway->>Appt: Confirm appointment
    Appt->>DB: Update status to CONFIRMED
    Appt->>SMS: Send confirmation
    SMS-->>Patient: SMS notification
    Appt-->>Gateway: Success
    Gateway-->>UI: Booking confirmed
    UI-->>Patient: "Appointment booked!"
```

---

## 7. Deployment Architecture

```mermaid
graph TB
    subgraph "Docker Compose Environment"
        subgraph "Network: telehealth_network"
            GW[api-gateway<br/>FastAPI<br/>Port: 8000]
            
            AUTH[auth-service<br/>Port: 8001]
            DOC[doctor-service<br/>Port: 8002]
            PAT[patient-service<br/>Port: 8003]
            APPT[appointment-service<br/>Port: 8004]
            TRI[triage-service<br/>Port: 8005]
            BSP[bsp-service<br/>Port: 8006]
            WND[wound-triage-api<br/>Port: 8007]
            CHT[chat-service<br/>Port: 8008]
            REC[records-service<br/>Port: 8009]
            FAM[family-service<br/>Port: 8010]
            NOT[notification-service<br/>Port: 8011]
            SMS[sms-service<br/>Port: 8012]
            ADM[admin-service<br/>Port: 8013]
        end
        
        DB[PostgreSQL<br/>Container<br/>Port: 5432]
        
        FRONT[Frontend<br/>Static Files<br/>Nginx Server]
    end

    subgraph "External"
        CLIENT[Web Browser]
        EXT_API[External APIs<br/>LLM, Cohere, Sarvam]
    end

    CLIENT -->|HTTP/WS| FRONT
    FRONT -->|Proxy| GW
    
    GW --> AUTH
    GW --> DOC
    GW --> PAT
    GW --> APPT
    GW --> TRI
    GW --> BSP
    GW --> WND
    GW --> CHT
    GW --> REC
    GW --> FAM
    GW --> NOT
    GW --> SMS
    GW --> ADM

    AUTH --> DB
    DOC --> DB
    PAT --> DB
    APPT --> DB
    CHT --> DB
    REC --> DB
    FAM --> DB

    TRI --> EXT_API

    style GW fill:#4285f4,color:#fff
    style DB fill:#336791,color:#fff
    style FRONT fill:#42A5F5,color:#fff
```

---

## System Metrics

- **Total Microservices**: 13
- **Frontend Pages**: 3 (Doctor Dashboard, Patient Dashboard, Login)
- **Database Tables**: 12+ core entities
- **External Integrations**: 4 (LLM, Cohere, Sarvam, Twilio)
- **Communication Protocols**: REST API, WebSocket
- **Authentication**: JWT-based

## Key Technologies

| Layer | Technologies |
|-------|-------------|
| **Frontend** | HTML5, CSS3, JavaScript (Vanilla) |
| **Backend** | Python 3.11, FastAPI |
| **Database** | PostgreSQL, SQLAlchemy ORM |
| **AI/ML** | LLM, Cohere, TensorFlow |
| **Voice** | Sarvam AI (Hinglish STT) |
| **Messaging** | WebSocket, Twilio SMS |
| **Deployment** | Docker, Docker Compose |
| **Architecture** | Microservices, API Gateway Pattern |
