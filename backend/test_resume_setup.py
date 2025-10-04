"""
TEMPORARY TEST SCRIPT - For Resume Feature Testing
Run this script to create a fake resumable batch for testing resume functionality.
"""

import uuid
import json
from pathlib import Path
from services.progress_tracker import progress_tracker, ProcessingStatus, BatchProgress, HospitalProgress

def create_test_resumable_batch():
    """Create a fake resumable batch for testing"""
    
    # Generate test data
    batch_id = str(uuid.uuid4())
    
    # Create fake hospital progress (3 successful, 2 failed)
    hospitals = [
        HospitalProgress(row=1, name="General Hospital", status="created", hospital_id=101, processing_time=5.2),
        HospitalProgress(row=2, name="City Medical Center", status="created", hospital_id=102, processing_time=4.8), 
        HospitalProgress(row=3, name="Metro Health", status="created", hospital_id=103, processing_time=6.1),
        HospitalProgress(row=4, name="Emergency Center", status="failed", error_message="Connection timeout", processing_time=3.5),
        HospitalProgress(row=5, name="Pediatric Hospital", status="failed", error_message="API error", processing_time=2.1),
    ]
    
    # Create batch progress
    progress = BatchProgress(
        batch_id=batch_id,
        status=ProcessingStatus.RESUMABLE,
        total_hospitals=5,
        processed_hospitals=3,
        failed_hospitals=2,
        hospitals=hospitals,
        is_resumable=True,
        resume_from_row=4,
        failure_reason="Simulated failure for testing resume capability",
        original_csv_data=[
            {"name": "General Hospital", "address": "123 Main St", "phone": "555-0123"},
            {"name": "City Medical Center", "address": "456 Oak Ave", "phone": "555-0456"},
            {"name": "Metro Health", "address": "789 Pine Rd", "phone": "555-0789"},
            {"name": "Emergency Center", "address": "321 Elm St", "phone": "555-0321"},
            {"name": "Pediatric Hospital", "address": "654 Maple Ave", "phone": ""},
        ]
    )
    
    # Store in progress tracker
    progress_tracker._progress_store[batch_id] = progress
    progress_tracker._save_batch_to_disk(progress)
    
    print(f"✅ Created test resumable batch: {batch_id}")
    print(f"📁 Saved to: batch_storage/{batch_id}.json")
    print(f"🔄 Resume from row: {progress.resume_from_row}")
    print(f"✅ Processed: {progress.processed_hospitals}")
    print(f"❌ Failed: {progress.failed_hospitals}")
    print(f"\n🧪 Test with:")
    print(f"GET /hospitals/resumable")
    print(f"POST /hospitals/resume/{batch_id}")
    
    return batch_id

if __name__ == "__main__":
    # Ensure batch_storage directory exists
    Path("batch_storage").mkdir(exist_ok=True)
    create_test_resumable_batch()