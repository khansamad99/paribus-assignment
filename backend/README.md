# Hospital Bulk Processing API

A FastAPI application for bulk processing hospital records via CSV upload.

## Setup

1. Activate virtual environment:
```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `POST /hospitals/bulk` - Bulk create hospitals from CSV

## CSV Format

```csv
name,address,phone
General Hospital,123 Main St,555-1234
City Medical Center,456 Oak Ave,555-5678
```

Note: `phone` is optional, `name` and `address` are required.