# Hospital Bulk Processing API

A high-performance FastAPI application for bulk processing hospital records via CSV upload with concurrent processing optimizations.

## 🚀 Quick Start

### Setup
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

4. Access API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📋 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Root endpoint with API info |
| `GET` | `/health` | Health check |
| `POST` | `/hospitals/bulk` | Bulk create hospitals from CSV |
| `POST` | `/hospitals/validate` | Validate CSV format before processing |
| `GET` | `/hospitals/progress/{batch_id}` | Get real-time progress for batch |
| `POST` | `/hospitals/progress/cleanup` | Clean up old progress data |

## 📄 CSV Format

```csv
name,address,phone
General Hospital,123 Main St,555-1234
City Medical Center,456 Oak Ave,555-5678
Metropolitan Health Center,789 Pine Rd,
```

**Requirements:**
- **Required fields**: `name`, `address`
- **Optional fields**: `phone` (can be empty)
- **Maximum**: 20 hospitals per file
- **Format**: UTF-8 encoded CSV

## 🔧 Configuration

Performance settings in `config.py`:
```python
MAX_CONCURRENT_REQUESTS = 10        # Concurrent API calls
HTTP_TIMEOUT_SECONDS = 30          # Total request timeout
HTTP_CONNECT_TIMEOUT_SECONDS = 10  # Connection timeout
MAX_CSV_SIZE = 20                  # Maximum hospitals per CSV
```

## ⚡ Performance Features

### Concurrent Processing
- **Sequential Processing**: 20 hospitals × 6s = 120 seconds
- **Concurrent Processing**: 20 hospitals in ~6-7 seconds (95% faster!)
- **Rate Limiting**: Semaphore controls concurrent requests to prevent API overload

### HTTP Optimizations
- **Connection Pooling**: Reuses connections (max 20 keepalive, 100 total)
- **Optimized Timeouts**: Separate connect (10s) and total (30s) timeouts
- **Error Handling**: Comprehensive error handling with detailed responses

### Progress Tracking
- **Real-time Progress**: Monitor bulk processing status in real-time
- **Hospital-level Tracking**: Individual hospital processing status and timing
- **Progress Percentage**: Automatic progress calculation and completion status
- **Thread-safe Operations**: Concurrent access to progress data

### Enhanced Validation
- **Pre-processing Validation**: Validate CSV before bulk processing
- **Detailed Error Reporting**: Row-level error identification with specific messages
- **Data Validation**: Name, address, phone number format validation
- **File Analysis**: Encoding, size, and format verification

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   CSV Upload    │───▶│  CSV Validator   │───▶│  Progress Tracker   │
│   (FastAPI)     │    │  (Enhanced)      │    │  (Real-time)        │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
                              │                           │
                              ▼                           ▼
                       ┌──────────────────┐    ┌─────────────────────┐
                       │  Bulk Processor  │───▶│  Hospital Directory │
                       │  (Concurrent)    │    │       API           │
                       └──────────────────┘    └─────────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │ Batch Activation │
                       └──────────────────┘
```

### Core Components

1. **CSV Processor** (`services/csv_processor.py`)
   - **Enhanced Validation**: Detailed validation with row-level error reporting
   - **Data Validation**: Name (2-255 chars), address (5-500 chars), phone format
   - **File Analysis**: Encoding detection, header validation, duplicate checking
   - **Preview Generation**: Shows first 5 valid hospitals for verification

2. **Progress Tracker** (`services/progress_tracker.py`)
   - **Real-time Progress**: Thread-safe in-memory progress tracking
   - **Hospital-level Status**: Individual processing status and timing
   - **Progress States**: initializing, validating, processing, activating, completed, failed
   - **Automatic Cleanup**: Removes old progress data (24+ hours)

3. **Hospital API Service** (`services/hospital_api.py`)
   - **HTTP Client Optimization**: Connection pooling (20 keepalive, 100 max)
   - **Concurrent Support**: Optimized timeouts and connection limits
   - **Batch Operations**: Individual hospital creation and batch activation
   - **Error Handling**: Comprehensive error handling and retry logic

4. **Bulk Router** (`routers/hospitals.py`)
   - **Concurrent Processing**: Semaphore-controlled concurrent hospital creation
   - **Progress Integration**: Real-time progress updates during processing
   - **Enhanced Validation**: Pre-processing CSV validation endpoint
   - **Performance Monitoring**: Detailed timing and logging

## 📊 API Responses

### Bulk Processing Response
```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_hospitals": 4,
  "processed_hospitals": 4,
  "failed_hospitals": 0,
  "processing_time_seconds": 6.01,
  "batch_activated": true,
  "hospitals": [
    {
      "row": 1,
      "hospital_id": 101,
      "name": "General Hospital",
      "status": "created_and_activated"
    }
  ]
}
```

### CSV Validation Response
```json
{
  "is_valid": true,
  "total_rows": 4,
  "valid_rows": 4,
  "invalid_rows": 0,
  "errors": [],
  "warnings": [],
  "preview_hospitals": [
    {
      "name": "General Hospital",
      "address": "123 Main Street New York NY 10001",
      "phone": "555-0123"
    }
  ],
  "file_info": {
    "size_bytes": 265,
    "encoding": "utf-8",
    "delimiter": ",",
    "has_header": true
  }
}
```

### Progress Tracking Response
```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "total_hospitals": 4,
  "processed_hospitals": 2,
  "failed_hospitals": 0,
  "progress_percentage": 50.0,
  "processing_time_seconds": 3.2,
  "current_step": "Processing hospitals concurrently",
  "batch_activated": false,
  "hospitals": [
    {
      "row": 1,
      "name": "General Hospital",
      "status": "created",
      "hospital_id": 101,
      "processing_time": 5.39
    },
    {
      "row": 2,
      "name": "City Medical Center",
      "status": "processing",
      "hospital_id": null,
      "processing_time": null
    }
  ],
  "is_completed": false
}
```

## 🔍 Processing Workflow

### Enhanced CSV Validation (Optional)
1. **Pre-processing Validation** via `POST /hospitals/validate`
   - Detailed CSV format and data validation
   - Row-level error identification and reporting
   - Preview of valid hospitals and file analysis
   - No data is processed or stored

### Bulk Processing Workflow
1. **Upload & Validation**
   - Validate CSV file format and basic structure
   - Parse and validate hospital data using enhanced validation
   - Generate unique batch ID (UUID)
   - Initialize progress tracking

2. **Progress Tracking Setup**
   - Create progress tracker entry with hospital names
   - Set initial status to "initializing"
   - Enable real-time progress monitoring

3. **Concurrent Processing**
   - Update status to "processing"
   - Create semaphore for rate limiting (max 10 concurrent)
   - Process hospitals concurrently with individual progress updates
   - Track processing time for each hospital

4. **Batch Activation**
   - Update status to "activating"
   - Activate entire batch if all hospitals created successfully
   - Update hospital statuses to "created_and_activated"

5. **Completion & Response**
   - Mark progress as "completed"
   - Compile comprehensive processing results
   - Include performance metrics and detailed status
   - Maintain progress data for future queries

## 🚀 Deployment

### Local Testing
```bash
# Validate CSV before processing
curl -X POST "http://localhost:8000/hospitals/validate" \
  -F "file=@sample_hospitals.csv"

# Bulk process hospitals
curl -X POST "http://localhost:8000/hospitals/bulk" \
  -F "file=@sample_hospitals.csv"

# Track progress (replace {batch_id} with actual batch ID)
curl "http://localhost:8000/hospitals/progress/{batch_id}"
```

### Production (Render)
- Automatic deployment from GitHub
- Environment: Python 3.11
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Docker Access:**
- Application: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## 🧪 Testing

Sample CSV file included in project root: `sample_hospitals.csv`

### Performance Benchmarks
- **4 hospitals**: ~6 seconds (concurrent) vs ~24 seconds (sequential)
- **20 hospitals**: ~6-7 seconds (concurrent) vs ~120 seconds (sequential)
- **95% performance improvement** through concurrent processing
- **Real-time Progress**: Sub-second progress updates during processing
- **Validation Speed**: CSV validation completes in <1 second for 20 hospitals

## 🛠️ External Dependencies

**Hospital Directory API**: `https://hospital-directory.onrender.com`
- Individual hospital CRUD operations
- Batch processing support
- Batch activation endpoints

## 📝 Error Handling

### Enhanced CSV Validation
- **Format Errors**: Invalid encoding, missing headers, malformed CSV
- **Data Validation**: Name length (2-255), address length (5-500), phone format
- **File Constraints**: Maximum 20 hospitals, UTF-8 encoding required
- **Row-level Errors**: Specific error messages with row and column identification

### Processing Errors
- **API Failures**: Individual hospital creation failures don't stop processing
- **Network Issues**: Connection timeouts, external API unavailability
- **Concurrent Safety**: Thread-safe progress tracking and error reporting
- **Batch Failures**: Partial success handling with detailed error reporting

### Progress Tracking
- **Real-time Updates**: Progress continues even if individual hospitals fail
- **Error Persistence**: Failed hospital details stored in progress data
- **Cleanup Handling**: Automatic cleanup of old progress data
- **Thread Safety**: Concurrent access protection for progress updates