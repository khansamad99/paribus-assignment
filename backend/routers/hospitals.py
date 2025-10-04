import time
import uuid
import asyncio
from fastapi import APIRouter, File, UploadFile, HTTPException
from typing import List, Tuple
from models import BulkProcessingResult, ProcessedHospital, ProgressResponse, HospitalProgressResponse, CSVValidationResult, ResumableBatch, ResumeResult
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
                    status="created",
                    processing_time=hospital_time
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
                    error_message="API call failed",
                    processing_time=hospital_time
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
                error_message=str(e),
                processing_time=hospital_time
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
    
    # Store CSV data for potential resume operations
    csv_data = []
    for hospital in hospitals:
        csv_data.append({
            'name': hospital.name,
            'address': hospital.address,
            'phone': hospital.phone
        })
    
    # Initialize progress tracking
    hospital_names = [hospital.name for hospital in hospitals]
    progress = progress_tracker.create_batch_progress(batch_id, len(hospitals), hospital_names)
    progress.original_csv_data = csv_data  # Store for resume capability
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
        # Mark batch as resumable for recovery
        progress_tracker.mark_batch_resumable(batch_id, f"Processing failed: {str(e)}", csv_data)
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

@router.get("/resumable", response_model=List[ResumableBatch])
async def get_resumable_batches():
    """
    Get all batches that can be resumed after failure
    """
    resumable_batches = progress_tracker.get_resumable_batches()
    return [ResumableBatch(**batch) for batch in resumable_batches]

@router.post("/resume/{batch_id}", response_model=BulkProcessingResult)
async def resume_bulk_processing(batch_id: str):
    """
    Resume a failed bulk processing operation from where it left off
    """
    # Load the batch for resume
    progress = progress_tracker.load_batch_for_resume(batch_id)
    
    if not progress:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    if not progress.is_resumable or progress.status != ProcessingStatus.RESUMABLE:
        raise HTTPException(status_code=400, detail="Batch is not resumable")
    
    start_time = time.time()
    
    # Update status to processing
    progress.status = ProcessingStatus.PROCESSING
    progress.resume_count += 1
    progress.current_step = f"Resuming processing from row {progress.resume_from_row}"
    
    # Initialize API service
    api_service = HospitalAPIService()
    
    try:
        # Get hospitals to process (from CSV data)
        hospitals_to_process = []
        for i, csv_row in enumerate(progress.original_csv_data, start=1):
            if i >= progress.resume_from_row:
                # Check if this hospital was already processed successfully
                existing_hospital = next((h for h in progress.hospitals if h.row == i), None)
                if not existing_hospital or existing_hospital.status not in ["created", "created_and_activated"]:
                    hospitals_to_process.append((i, csv_row))
        
        if not hospitals_to_process:
            # All hospitals already processed, just activate if needed
            progress.current_step = "All hospitals already processed, checking activation"
        else:
            # Process remaining hospitals concurrently
            max_concurrent_requests = min(settings.MAX_CONCURRENT_REQUESTS, len(hospitals_to_process))
            semaphore = asyncio.Semaphore(max_concurrent_requests)
            
            print(f"Resuming {len(hospitals_to_process)} hospitals with {max_concurrent_requests} concurrent connections")
            
            # Create tasks for unprocessed hospitals
            tasks = []
            for row_num, csv_row in hospitals_to_process:
                # Create hospital object from CSV data
                from models import HospitalCreate
                hospital = HospitalCreate(
                    name=csv_row['name'],
                    address=csv_row['address'],
                    phone=csv_row.get('phone')
                )
                
                tasks.append(
                    process_hospital_concurrent(api_service, hospital, batch_id, row_num, semaphore)
                )
            
            # Execute concurrent processing
            new_results = await asyncio.gather(*tasks, return_exceptions=False)
            
            # Update progress with new results
            for result in new_results:
                # Update or add hospital progress
                existing_idx = next((i for i, h in enumerate(progress.hospitals) if h.row == result.row), None)
                if existing_idx is not None:
                    progress.hospitals[existing_idx] = result
                else:
                    progress.hospitals.append(result)
        
        # Recalculate counts
        successful_count = sum(1 for h in progress.hospitals if h.status == "created")
        failed_count = sum(1 for h in progress.hospitals if h.status == "failed")
        
        # Update progress counts
        progress.processed_hospitals = successful_count
        progress.failed_hospitals = failed_count
        
        # Try to activate batch if all successful
        batch_activated = False
        if successful_count > 0 and failed_count == 0:
            progress.current_step = "Activating hospital batch"
            batch_activated = await api_service.activate_batch(batch_id)
            
            if batch_activated:
                progress.batch_activated = True
                for hospital in progress.hospitals:
                    if hospital.status == "created":
                        hospital.status = "created_and_activated"
        
        # Mark as completed or failed
        if failed_count == 0:
            progress_tracker.complete_batch(batch_id, batch_activated)
        else:
            # Still has failures, mark as resumable again
            csv_data = progress.original_csv_data
            progress_tracker.mark_batch_resumable(batch_id, f"Resume attempt {progress.resume_count} completed with {failed_count} failures", csv_data)
        
        processing_time = time.time() - start_time
        
        return BulkProcessingResult(
            batch_id=batch_id,
            total_hospitals=progress.total_hospitals,
            processed_hospitals=successful_count,
            failed_hospitals=failed_count,
            processing_time_seconds=round(processing_time, 2),
            batch_activated=batch_activated,
            hospitals=[ProcessedHospital(
                row=h.row,
                hospital_id=h.hospital_id,
                name=h.name,
                status=h.status,
                error_message=h.error_message,
                processing_time=h.processing_time
            ) for h in progress.hospitals]
        )
        
    except Exception as e:
        # Mark batch as resumable with error
        csv_data = progress.original_csv_data
        progress_tracker.mark_batch_resumable(batch_id, f"Resume failed: {str(e)}", csv_data)
        raise HTTPException(status_code=500, detail=f"Resume operation failed: {str(e)}")
    finally:
        await api_service.close()

@router.delete("/batch/{batch_id}/abandon")
async def abandon_batch(batch_id: str):
    """
    Abandon a failed batch and clean up its data
    """
    progress = progress_tracker.get_progress(batch_id)
    
    if not progress:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    # Clean up the batch
    progress_tracker._delete_batch_from_disk(batch_id)
    
    with progress_tracker._lock:
        if batch_id in progress_tracker._progress_store:
            del progress_tracker._progress_store[batch_id]
    
    return {"message": f"Batch {batch_id} has been abandoned and cleaned up"}

