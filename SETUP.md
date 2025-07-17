# Ytili Platform Setup Guide

**Ytili** - AI Agent for Transparent Medical Donations  
*"Save for health, give when you can"*

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** (Required)
- **PostgreSQL 13+** (Required)
- **Redis 6+** (Optional, for background tasks)
- **OpenRouter API Key** (Required for AI features in Phase 2)

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd ytili

# Make the development runner executable
chmod +x run_dev.py
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your configuration
```

### 3. Database Setup

```bash
# Create PostgreSQL database
createdb ytili_db

# Create database user (optional)
psql -c "CREATE USER ytili_user WITH PASSWORD 'ytili_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE ytili_db TO ytili_user;"

# Run migrations (auto-created in development)
# Database tables will be created automatically when you start the server
```

### 4. Frontend Setup

```bash
cd ../frontend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your configuration
```

### 5. Run the Platform

```bash
# From the project root directory
python run_dev.py
```

This will start both servers:
- **Backend API**: http://localhost:8000
- **Frontend Web**: http://localhost:5000

## 🔧 Configuration

### Backend Environment (.env)

```env
# Application
DEBUG=True
SECRET_KEY=your-super-secret-key-change-this

# Database
DATABASE_URL=postgresql://ytili_user:ytili_password@localhost:5432/ytili_db

# OpenRouter API (for AI features)
OPENROUTER_API_KEY=your-openrouter-api-key
PRIMARY_MODEL=qwen/qwen3-235b-a22b:free

# Redis (optional)
REDIS_URL=redis://localhost:6379

# Email (optional)
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Stripe (for payments)
STRIPE_PUBLISHABLE_KEY=pk_test_your_key
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_secret
```

### Frontend Environment (.env)

```env
# Flask
FLASK_ENV=development
SECRET_KEY=your-super-secret-key-change-this

# Backend API
BACKEND_API_URL=http://localhost:8000
```

## 📚 API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🏥 Default Admin Account

The system creates a default admin account:
- **Email**: admin@ytili.com
- **Password**: admin123
- **Type**: Government (Admin)

## 🧪 Testing the Platform

### 1. Register Users

1. Visit http://localhost:5000
2. Click "Register" 
3. Create accounts for different user types:
   - Individual donor
   - Hospital
   - Organization

### 2. Create Donations

1. Login as an individual user
2. Go to "Donations" → "Create Donation"
3. Fill in donation details
4. Submit donation

### 3. View Transparency

1. Visit http://localhost:5000/transparency
2. View public transparency dashboard
3. Check donation transaction chains
4. Verify platform integrity score

### 4. Admin Features

1. Login as admin (admin@ytili.com / admin123)
2. Access admin-only features:
   - KYC document verification
   - Fraud detection dashboard
   - Transaction search

## 🔍 Key Features Implemented (Phase 1)

### ✅ Authentication & User Management
- Multi-tier user registration (individual, hospital, organization, government)
- Email verification system
- Role-based access control
- KYC document upload and verification with OCR

### ✅ Donation System
- Medication/supply catalog with search
- Donation creation and tracking
- Intelligent matching system for hospitals
- Payment processing with Stripe integration

### ✅ Transparency Infrastructure
- Blockchain-inspired transaction logging
- Public transparency dashboard
- Chain integrity verification
- Real-time donation tracking

### ✅ Fraud Detection
- Suspicious activity monitoring
- User risk scoring
- Automated fraud alerts
- Admin fraud dashboard

## 🛠️ Development

### Project Structure

```
ytili/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── core/           # Configuration, security
│   │   ├── models/         # Database models
│   │   ├── services/       # Business logic
│   │   └── main.py         # Application entry point
│   ├── alembic/            # Database migrations
│   └── requirements.txt
├── frontend/               # Flask frontend
│   ├── app/
│   │   ├── templates/      # Jinja2 templates
│   │   ├── routes/         # Flask routes
│   │   └── main.py         # Application entry point
│   └── requirements.txt
├── run_dev.py              # Development server runner
└── README.md
```

### Adding New Features

1. **Backend API**: Add routes in `backend/app/api/`
2. **Frontend Pages**: Add templates in `frontend/app/templates/`
3. **Database Models**: Add models in `backend/app/models/`
4. **Business Logic**: Add services in `backend/app/services/`

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
pytest
```

## 🚀 Next Steps (Phase 2)

The platform is ready for Phase 2 development:

1. **AI Agent Integration**
   - OpenRouter API integration
   - Donation advisory chatbot
   - Intelligent recommendation system

2. **Advanced Features**
   - Points/rewards system
   - Emergency support requests
   - Community voting mechanism

3. **Mobile App**
   - React Native mobile application
   - Push notifications
   - Offline support

## 🆘 Troubleshooting

### Common Issues

1. **Database Connection Error**
   ```bash
   # Check if PostgreSQL is running
   sudo systemctl status postgresql
   
   # Check database exists
   psql -l | grep ytili_db
   ```

2. **Port Already in Use**
   ```bash
   # Kill processes on ports 8000 and 5000
   sudo lsof -ti:8000 | xargs kill -9
   sudo lsof -ti:5000 | xargs kill -9
   ```

3. **Module Import Errors**
   ```bash
   # Ensure virtual environment is activated
   source venv/bin/activate
   
   # Reinstall dependencies
   pip install -r requirements.txt
   ```

### Getting Help

- Check the logs in the terminal where you ran `python run_dev.py`
- Visit the API documentation at http://localhost:8000/docs
- Review the error messages in the browser console

## 📄 License

This project is licensed under the MIT License.

---

**Ytili Platform** - Empowering transparent healthcare donations through AI technology.
