import csv
import io
from typing import List, Tuple
from fastapi import HTTPException
from models import HospitalCreate
from config import settings

class CSVProcessor:
    @staticmethod
    def validate_and_parse_csv(file_content: bytes) -> List[HospitalCreate]:
        """Validate and parse CSV file content"""
        try:
            # Decode bytes to string
            content = file_content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content))
            
            # Validate headers
            if not csv_reader.fieldnames:
                raise HTTPException(status_code=400, detail="CSV file is empty or has no headers")
            
            required_columns = settings.CSV_REQUIRED_COLUMNS
            missing_columns = [col for col in required_columns if col not in csv_reader.fieldnames]
            if missing_columns:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Missing required columns: {missing_columns}"
                )
            
            hospitals = []
            for row_num, row in enumerate(csv_reader, start=1):
                # Skip empty rows
                if not any(row.values()):
                    continue
                
                # Validate required fields
                name = row.get('name', '').strip()
                address = row.get('address', '').strip()
                
                if not name:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Row {row_num}: Name is required"
                    )
                if not address:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Row {row_num}: Address is required"
                    )
                
                # Get optional phone field
                phone = row.get('phone', '').strip() or None
                
                hospitals.append(HospitalCreate(
                    name=name,
                    address=address,
                    phone=phone
                ))
            
            if not hospitals:
                raise HTTPException(status_code=400, detail="No valid hospital records found in CSV")
            
            if len(hospitals) > settings.MAX_CSV_SIZE:
                raise HTTPException(
                    status_code=400, 
                    detail=f"CSV contains {len(hospitals)} hospitals. Maximum allowed is {settings.MAX_CSV_SIZE}"
                )
            
            return hospitals
            
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Invalid CSV file encoding. Please use UTF-8")
        except csv.Error as e:
            raise HTTPException(status_code=400, detail=f"CSV parsing error: {str(e)}")
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")