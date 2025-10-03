import time
import uuid
from fastapi import APIRouter, File, UploadFile, HTTPException
from typing import List
from models import BulkProcessingResult, ProcessedHospital
from services.csv_processor import CSVProcessor
from services.hospital_api import HospitalAPIService

router = APIRouter()

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
        # Process each hospital
        for row_num, hospital in enumerate(hospitals, start=1):
            try:
                result = await api_service.create_hospital(hospital, batch_id)
                if result:
                    processed_hospitals.append(ProcessedHospital(
                        row=row_num,
                        hospital_id=result.id,
                        name=hospital.name,
                        status="created"
                    ))
                    successful_count += 1
                else:
                    processed_hospitals.append(ProcessedHospital(
                        row=row_num,
                        hospital_id=None,
                        name=hospital.name,
                        status="failed",
                        error_message="API call failed"
                    ))
                    failed_count += 1
            except Exception as e:
                processed_hospitals.append(ProcessedHospital(
                    row=row_num,
                    hospital_id=None,
                    name=hospital.name,
                    status="failed",
                    error_message=str(e)
                ))
                failed_count += 1
        
        # Activate batch if all hospitals were created successfully
        batch_activated = False
        if successful_count > 0 and failed_count == 0:
            batch_activated = await api_service.activate_batch(batch_id)
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