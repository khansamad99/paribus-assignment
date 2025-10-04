import time
import uuid
import asyncio
from fastapi import APIRouter, File, UploadFile, HTTPException
from typing import List, Tuple
from models import BulkProcessingResult, ProcessedHospital, ProgressResponse, HospitalProgressResponse, CSVValidationResult
from services.csv_processor import CSVProcessor
from services.hospital_api import HospitalAPIService
from services.progress_tracker import progress_tracker, ProcessingStatus
from config import settings

router = APIRouter()

async def process_hospital_concurrent(
    api_service: HospitalAPIService, 
    hospital, 
    batch_id: str, 
    row_num: int,
    semaphore: asyncio.Semaphore
) -> ProcessedHospital:
    """Process a single hospital with concurrency control and progress tracking"""
    async with semaphore:  # Limit concurrent connections
        hospital_start = time.time()
        
        # Update progress: starting processing
        progress_tracker.update_hospital_progress(batch_id, row_num, "processing")
        
        try:
            result = await api_service.create_hospital(hospital, batch_id)
            hospital_time = time.time() - hospital_start
            print(f"Hospital {row_num} '{hospital.name}' processed in {hospital_time:.2f}s")
            
            if result:
                # Update progress: completed successfully
                progress_tracker.update_hospital_progress(
                    batch_id, row_num, "created", 
                    hospital_id=result.id, 
                    processing_time=hospital_time
                )
                
                return ProcessedHospital(
                    row=row_num,
                    hospital_id=result.id,
                    name=hospital.name,
                    status="created"
                )
            else:
                # Update progress: failed
                progress_tracker.update_hospital_progress(
                    batch_id, row_num, "failed", 
                    error_message="API call failed",
                    processing_time=hospital_time
                )
                
                return ProcessedHospital(
                    row=row_num,
                    hospital_id=None,
                    name=hospital.name,
                    status="failed",
                    error_message="API call failed"
                )
        except Exception as e:
            hospital_time = time.time() - hospital_start
            print(f"Hospital {row_num} '{hospital.name}' failed in {hospital_time:.2f}s - {str(e)}")
            
            # Update progress: failed with error
            progress_tracker.update_hospital_progress(
                batch_id, row_num, "failed", 
                error_message=str(e),
                processing_time=hospital_time
            )
            
            return ProcessedHospital(
                row=row_num,
                hospital_id=None,
                name=hospital.name,
                status="failed",
                error_message=str(e)
            )

@router.post("/bulk", response_model=BulkProcessingResult)
async def bulk_create_hospitals(file: UploadFile = File(...)):
    """
    Bulk create hospitals from CSV file
    CSV format: name,address,phone (phone is optional)
    Maximum 20 hospitals per file
    """
    start_time = time.time()
    
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    # Read and validate CSV
    content = await file.read()
    hospitals = CSVProcessor.validate_and_parse_csv(content)
    
    # Generate batch ID
    batch_id = str(uuid.uuid4())
    
    # Initialize progress tracking
    hospital_names = [hospital.name for hospital in hospitals]
    progress_tracker.create_batch_progress(batch_id, len(hospitals), hospital_names)
    progress_tracker.update_status(batch_id, ProcessingStatus.VALIDATING, "CSV validation completed")
    
    # Initialize API service
    api_service = HospitalAPIService()
    
    processed_hospitals = []
    successful_count = 0
    failed_count = 0
    
    try:
        # Update progress: starting processing
        progress_tracker.update_status(batch_id, ProcessingStatus.PROCESSING, "Starting concurrent hospital processing")
        
        # Process hospitals concurrently with connection limiting
        max_concurrent_requests = min(settings.MAX_CONCURRENT_REQUESTS, len(hospitals))  # Limit concurrent connections
        semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        print(f"Processing {len(hospitals)} hospitals with {max_concurrent_requests} concurrent connections")
        concurrent_start = time.time()
        
        # Create concurrent tasks for all hospitals
        tasks = [
            process_hospital_concurrent(api_service, hospital, batch_id, row_num, semaphore)
            for row_num, hospital in enumerate(hospitals, start=1)
        ]
        
        # Execute all tasks concurrently
        processed_hospitals = await asyncio.gather(*tasks, return_exceptions=False)
        
        concurrent_time = time.time() - concurrent_start
        print(f"Concurrent processing completed in {concurrent_time:.2f}s")
        
        # Count successful and failed operations
        successful_count = sum(1 for h in processed_hospitals if h.status == "created")
        failed_count = len(processed_hospitals) - successful_count
        
        # Activate batch if all hospitals were created successfully
        batch_activated = False
        if successful_count > 0 and failed_count == 0:
            # Update progress: activating batch
            progress_tracker.update_status(batch_id, ProcessingStatus.ACTIVATING, "Activating hospital batch")
            
            activation_start = time.time()
            batch_activated = await api_service.activate_batch(batch_id)
            activation_time = time.time() - activation_start
            print(f"Batch activation took {activation_time:.2f}s")
            
            if batch_activated:
                # Update status for all hospitals
                for hospital in processed_hospitals:
                    if hospital.status == "created":
                        hospital.status = "created_and_activated"
        
        # Complete progress tracking
        progress_tracker.complete_batch(batch_id, batch_activated)
        
        processing_time = time.time() - start_time
        
        return BulkProcessingResult(
            batch_id=batch_id,
            total_hospitals=len(hospitals),
            processed_hospitals=successful_count,
            failed_hospitals=failed_count,
            processing_time_seconds=round(processing_time, 2),
            batch_activated=batch_activated,
            hospitals=processed_hospitals
        )
        
    except Exception as e:
        # Mark batch as failed in progress tracker
        progress_tracker.mark_batch_failed(batch_id, str(e))
        raise
    finally:
        await api_service.close()

@router.get("/progress/{batch_id}", response_model=ProgressResponse)
async def get_batch_progress(batch_id: str):
    """
    Get real-time progress for a batch processing operation
    """
    progress = progress_tracker.get_progress(batch_id)
    
    if not progress:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    # Convert to response model
    hospital_responses = [
        HospitalProgressResponse(
            row=h.row,
            name=h.name,
            status=h.status,
            hospital_id=h.hospital_id,
            error_message=h.error_message,
            processing_time=h.processing_time
        )
        for h in progress.hospitals
    ]
    
    return ProgressResponse(
        batch_id=progress.batch_id,
        status=progress.status.value,
        total_hospitals=progress.total_hospitals,
        processed_hospitals=progress.processed_hospitals,
        failed_hospitals=progress.failed_hospitals,
        progress_percentage=progress.progress_percentage,
        processing_time_seconds=progress.processing_time_seconds,
        current_step=progress.current_step,
        batch_activated=progress.batch_activated,
        hospitals=hospital_responses,
        is_completed=progress.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]
    )

@router.post("/progress/cleanup")
async def cleanup_old_progress():
    """
    Clean up old progress tracking data (older than 24 hours)
    """
    cleaned_count = progress_tracker.cleanup_old_batches()
    return {"message": f"Cleaned up {cleaned_count} old batch progress records"}

@router.post("/validate", response_model=CSVValidationResult)
async def validate_csv(file: UploadFile = File(...)):
    """
    Validate CSV file format and content before processing
    Returns detailed validation results with errors, warnings, and preview
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    # Read file content
    content = await file.read()
    
    # Perform detailed validation
    validation_result = CSVProcessor.detailed_csv_validation(content)
    
    return validation_result

