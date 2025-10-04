# Local Development Setup Guide

Complete guide to set up and run the Hospital Bulk Processing API locally from scratch.

## 📋 Prerequisites

- **Python 3.11+** (recommended 3.11 or 3.12)
- **Git** (for cloning the repository)
- **Internet connection** (for external Hospital Directory API)

## 🚀 Step-by-Step Setup

### 1. Clone the Repository

```bash
# Clone the repository
git clone <repository-url>
cd Pairbus

# Navigate to the backend directory
cd backend
```

### 2. Create Virtual Environment

```bash
# Create a new virtual environment
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Verify activation (should show venv in prompt)
which python  # Should point to venv/bin/python
```

### 3. Install Dependencies

```bash
# Upgrade pip to latest version
pip install --upgrade pip

# Install all required packages
pip install -r requirements.txt

# Verify installation
pip list
```

Expected packages:
- fastapi
- uvicorn
- httpx
- pydantic
- python-multipart

### 4. Verify Project Structure

Your backend directory should look like this:
```
backend/
├── main.py                    # FastAPI application entry point
├── config.py                  # Configuration settings
├── models.py                  # Pydantic models
├── requirements.txt           # Python dependencies
├── routers/
│   ├── __init__.py
│   └── hospitals.py          # API endpoints
├── services/
│   ├── __init__.py
│   ├── csv_processor.py      # CSV validation and parsing
│   ├── hospital_api.py       # External API integration
│   └── progress_tracker.py   # Progress tracking system
├── sample_hospitals.csv      # Test data (10 hospitals)
├── large_sample_hospitals.csv # Test data (20 hospitals)
├── test_resume_setup.py      # Resume testing script
└── venv/                     # Virtual environment
```

### 5. Configure Environment (Optional)

Create a `.env` file for custom configuration:

```bash
# Create .env file (optional)
touch .env
```

Add custom settings (all have defaults):
```env
# .env file (optional - all settings have defaults)
APP_NAME="Hospital Bulk Processing API"
APP_VERSION="1.0.0"
MAX_CONCURRENT_REQUESTS=10
HTTP_TIMEOUT_SECONDS=30
HTTP_CONNECT_TIMEOUT_SECONDS=10
MAX_CSV_SIZE=20
PROGRESS_CLEANUP_HOURS=24
```

### 6. Start the Development Server

```bash
# Start the server with hot reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Alternative: Start with specific log level
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level info
```

Expected output:
```
INFO:     Will watch for changes in these directories: ['/path/to/backend']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 7. Verify Installation

Test the API endpoints:

```bash
# Test root endpoint
curl http://localhost:8000/

# Test health check
curl http://localhost:8000/health

# Access interactive documentation
open http://localhost:8000/docs
```

## 🧪 Testing Your Setup

### Basic API Test

```bash
# 1. Validate a CSV file
curl -X POST "http://localhost:8000/hospitals/validate" \
  -F "file=@sample_hospitals.csv"

# 2. Process hospitals
curl -X POST "http://localhost:8000/hospitals/bulk" \
  -F "file=@sample_hospitals.csv"

# 3. Check progress (replace with actual batch_id from step 2)
curl "http://localhost:8000/hospitals/progress/{batch_id}"
```

### Resume Feature Test

```bash
# Create mock resumable batch
python test_resume_setup.py

# List resumable batches
curl "http://localhost:8000/hospitals/resumable"

# Resume a batch (use batch_id from previous response)
curl -X POST "http://localhost:8000/hospitals/resume/{batch_id}"
```

## 🔧 Development Tools

### Interactive API Documentation

- **Swagger UI**: http://localhost:8000/docs
  - Interactive API testing interface
  - Upload files directly in browser
  - View request/response schemas

- **ReDoc**: http://localhost:8000/redoc
  - Clean API documentation
  - Detailed endpoint descriptions

### Server Management

```bash
# Start server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Start on different port
uvicorn main:app --reload --host 0.0.0.0 --port 8080

# Start without reload (production-like)
uvicorn main:app --host 0.0.0.0 --port 8000

# Stop server
# Press Ctrl+C in terminal
```

### Log Monitoring

```bash
# View detailed logs
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level debug

# Monitor processing in real-time
tail -f /path/to/logfile  # If logging to file
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. Virtual Environment Not Activated
**Error**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Verify activation
which python
```

#### 2. Port Already in Use
**Error**: `OSError: [Errno 48] Address already in use`

**Solution**:
```bash
# Use different port
uvicorn main:app --reload --host 0.0.0.0 --port 8001

# Or kill process using port 8000
lsof -ti:8000 | xargs kill -9  # macOS/Linux
```

#### 3. External API Connection Issues
**Error**: Connection timeout to Hospital Directory API

**Solution**:
- Check internet connection
- Verify external API status: https://hospital-directory.onrender.com
- Wait for cold start (Render free tier may take 30+ seconds)

#### 4. File Upload Issues
**Error**: `422 Unprocessable Entity` on file upload

**Solution**:
```bash
# Ensure correct file parameter name and CSV format
curl -X POST "http://localhost:8000/hospitals/bulk" \
  -F "file=@sample_hospitals.csv"
# NOT -F "csv=@file.csv"
```

#### 5. Permission Issues
**Error**: Permission denied errors

**Solution**:
```bash
# Fix file permissions
chmod +x main.py
chmod -R 755 backend/

# Or run with sudo (not recommended)
sudo uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Reset Development Environment

If you need to start fresh:

```bash
# Deactivate virtual environment
deactivate

# Remove virtual environment
rm -rf venv

# Recreate and reinstall
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Clean Up Storage

```bash
# Remove batch storage files
rm -rf batch_storage/

# Clean up old progress data via API
curl -X POST "http://localhost:8000/hospitals/progress/cleanup"
```

## 📊 Development Workflow

### Typical Development Session

```bash
# 1. Activate environment
cd backend
source venv/bin/activate

# 2. Start server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 3. Open documentation
open http://localhost:8000/docs

# 4. Test changes
curl -X POST "http://localhost:8000/hospitals/bulk" \
  -F "file=@sample_hospitals.csv"

# 5. Monitor logs in terminal
# 6. Make code changes (server auto-reloads)
# 7. Test again
```

### Making Changes

1. **Edit code** - Server auto-reloads with `--reload` flag
2. **Test endpoints** - Use Swagger UI or curl commands
3. **Check logs** - Monitor terminal output for errors
4. **Validate changes** - Test all affected endpoints

## 🌐 Switching to Production

To test against production instead of local:

```bash
# Use production URL in curl commands
curl "https://paribus-assignment.onrender.com/health"

# Or set environment variable
export BASE_URL="https://paribus-assignment.onrender.com"
curl "$BASE_URL/health"
```

## 📋 Quick Reference

### Essential Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Test
curl http://localhost:8000/health
curl -X POST "http://localhost:8000/hospitals/bulk" -F "file=@sample_hospitals.csv"

# Resume Testing
python test_resume_setup.py
curl "http://localhost:8000/hospitals/resumable"
```

### Important URLs

- **API Root**: http://localhost:8000/
- **Health Check**: http://localhost:8000/health
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Production**: https://paribus-assignment.onrender.com

Ready for local development! 🚀