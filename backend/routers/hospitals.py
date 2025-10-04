import time
import uuid
import asyncio
from fastapi import APIRouter, File, UploadFile, HTTPException
from typing import List, Tuple
from models import BulkProcessingResult, ProcessedHospital
from services.csv_processor import CSVProcessor
from services.hospital_api import HospitalAPIService
from config import settings

router = APIRouter()

async def process_hospital_concurrent(
    api_service: HospitalAPIService, 
    hospital, 
    batch_id: str, 
    row_num: int,
    semaphore: asyncio.Semaphore
) -> ProcessedHospital:
    """Process a single hospital with concurrency control"""
    async with semaphore:  # Limit concurrent connections
        hospital_start = time.time()
        try:
            result = await api_service.create_hospital(hospital, batch_id)
            hospital_time = time.time() - hospital_start
            print(f"Hospital {row_num} '{hospital.name}' processed in {hospital_time:.2f}s")
            
            if result:
                return ProcessedHospital(
                    row=row_num,
                    hospital_id=result.id,
                    name=hospital.name,
                    status="created"
                )
            else:
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
    
    # Initialize API service
    api_service = HospitalAPIService()
    
    processed_hospitals = []
    successful_count = 0
    failed_count = 0
    
    try:
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
            activation_start = time.time()
            batch_activated = await api_service.activate_batch(batch_id)
            activation_time = time.time() - activation_start
            print(f"Batch activation took {activation_time:.2f}s")
            
            if batch_activated:
                # Update status for all hospitals
                for hospital in processed_hospitals:
                    if hospital.status == "created":
                        hospital.status = "created_and_activated"
        
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
        
    finally:
        await api_service.close()