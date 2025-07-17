# Ytili - AI Agent for Transparent Medical Donations

**Mission**: "Save for health, give when you can"

Ytili is an AI-powered platform that facilitates transparent medical donations, connecting donors with hospitals and patients in need through intelligent matching and verification systems.

## 🏗️ Project Structure

```
ytili/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── core/           # Configuration, security
│   │   ├── models/         # Database models
│   │   ├── services/       # Business logic
│   │   └── ai_agent/       # AI integration
│   ├── alembic/            # Database migrations
│   ├── tests/              # Backend tests
│   └── requirements.txt
├── frontend/               # Flask frontend
│   ├── app/
│   │   ├── templates/      # Jinja2 templates
│   │   ├── static/         # CSS, JS, images
│   │   ├── routes/         # Flask routes
│   │   └── utils/          # Helper functions
│   ├── tests/              # Frontend tests
│   └── requirements.txt
└── docs/                   # Documentation
    ├── api/                # API documentation
    ├── user/               # User guides
    └── technical/          # Technical specifications
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 13+
- Redis 6+
- OpenRouter API key (for AI agent)

### Backend Setup

1. **Clone and navigate to backend**:
   ```bash
   cd backend
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Database setup**:
   ```bash
   # Create database
   createdb ytili_db
   
   # Run migrations
   alembic upgrade head
   ```

6. **Start backend server**:
   ```bash
   python -m app.main
   # Or with uvicorn
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. **Navigate to frontend**:
   ```bash
   cd frontend
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Start frontend server**:
   ```bash
   python -m app.main
   # Or with Flask CLI
   flask run --host 0.0.0.0 --port 5000
   ```

## 🔧 Configuration

### Backend Environment Variables

```env
# Application
DEBUG=True
SECRET_KEY=your-super-secret-key

# Database
DATABASE_URL=postgresql://ytili_user:ytili_password@localhost:5432/ytili_db

# OpenRouter API (NO OpenAI allowed per ruleset)
OPENROUTER_API_KEY=your-openrouter-api-key
PRIMARY_MODEL=qwen/qwen-2.5-72b-instruct

# Redis
REDIS_URL=redis://localhost:6379

# Email
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### Frontend Environment Variables

```env
# Flask
FLASK_ENV=development
SECRET_KEY=your-super-secret-key

# Backend API
BACKEND_API_URL=http://localhost:8000
```

## 🏥 Key Features

### Phase 1: Core Platform Foundation
- ✅ Multi-tier user registration (individual, hospital, organization)
- ✅ KYC verification system with document OCR
- ✅ Role-based access control and permissions
- ✅ Basic donation system with payment processing
- ✅ Transaction logging for transparency
- ✅ Basic fraud detection mechanisms

### Phase 2: AI Agent Integration (Coming Soon)
- 🔄 OpenRouter API integration with qwen model
- 🔄 Donation advisory chatbot
- 🔄 Intelligent matching algorithm
- 🔄 Points/rewards system
- 🔄 Emergency support requests
- 🔄 Community voting mechanism

### Phase 3: Scaling & Ecosystem (Planned)
- 📋 Fintech integration (BNPL, micro-insurance)
- 📋 Pharmacy network integration
- 📋 International expansion
- 📋 Government compliance dashboard

## 🔐 Security & Compliance

- **Healthcare Data Protection**: End-to-end encryption for medical data
- **Fraud Prevention**: Multi-layer verification and anomaly detection
- **Regulatory Compliance**: Vietnamese pharmaceutical and financial regulations
- **Audit Trail**: Immutable transaction records for transparency
- **Privacy**: User consent management and data minimization

## 🤖 AI Agent Integration

The platform uses **OpenRouter API** with the **qwen/qwen-2.5-72b-instruct** model as the primary AI agent for:

- Medical donation advisory (with appropriate disclaimers)
- Intelligent matching of donations to needs
- Fraud detection and prevention
- Multilingual support (Vietnamese and English)

**Note**: No OpenAI packages are used in compliance with project requirements.

## 📊 API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
pytest
```

## 🚀 Deployment

### Production Checklist
- [ ] Set `DEBUG=False` in environment
- [ ] Use production database
- [ ] Configure proper CORS origins
- [ ] Set up SSL/TLS certificates
- [ ] Configure monitoring (Sentry)
- [ ] Set up backup strategies
- [ ] Configure load balancing

## 🤝 Contributing

1. Follow the development ruleset in `.augment/rules/rules.md`
2. Use the specified tech stack (FastAPI + Flask + Python)
3. Maintain security and compliance standards
4. Write comprehensive tests
5. Document all changes

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Email: support@ytili.com
- Documentation: `/docs`
- Issues: GitHub Issues

---

**Ytili** - Empowering transparent healthcare donations through AI technology.
