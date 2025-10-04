import csv
import io
import re
from typing import List, Tuple, Dict, Any
from fastapi import HTTPException
from models import HospitalCreate, ValidationError, CSVValidationResult
from config import settings

class CSVProcessor:
    
    @staticmethod
    def _validate_phone_number(phone: str) -> bool:
        """Validate phone number format (basic validation)"""
        if not phone.strip():
            return True  # Empty phone is allowed
        
        # Remove common phone number separators and spaces
        clean_phone = re.sub(r'[\s\-\(\)\.]', '', phone)
        
        # Basic validation: 7-15 digits, optionally starting with +
        # Allows formats like: 555-0123 (7 digits), (555) 012-3456 (10 digits), +1-555-012-3456, etc.
        pattern = r'^\+?\d{7,15}$'
        return bool(re.match(pattern, clean_phone))
    
    @staticmethod
    def _validate_name(name: str) -> bool:
        """Validate hospital name"""
        if not name or not name.strip():
            return False
        if len(name.strip()) < 2:
            return False
        if len(name.strip()) > 255:
            return False
        return True
    
    @staticmethod
    def _validate_address(address: str) -> bool:
        """Validate hospital address"""
        if not address or not address.strip():
            return False
        if len(address.strip()) < 5:
            return False
        if len(address.strip()) > 500:
            return False
        return True
    
    @staticmethod
    def detailed_csv_validation(file_content: bytes) -> CSVValidationResult:
        """Perform detailed CSV validation with comprehensive error reporting"""
        errors = []
        warnings = []
        valid_hospitals = []
        
        try:
            # Decode bytes to string
            content = file_content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content))
            
            # File info
            file_info = {
                "size_bytes": len(file_content),
                "encoding": "utf-8",
                "delimiter": ",",
                "has_header": True
            }
            
            # Validate headers
            if not csv_reader.fieldnames:
                errors.append(ValidationError(
                    row=0,
                    column="header",
                    value="",
                    error_type="missing_header",
                    message="CSV file is empty or has no headers"
                ))
                return CSVValidationResult(
                    is_valid=False,
                    total_rows=0,
                    valid_rows=0,
                    invalid_rows=0,
                    errors=errors,
                    warnings=warnings,
                    preview_hospitals=[],
                    file_info=file_info
                )
            
            # Check required columns
            required_columns = settings.CSV_REQUIRED_COLUMNS
            missing_columns = [col for col in required_columns if col not in csv_reader.fieldnames]
            if missing_columns:
                for col in missing_columns:
                    errors.append(ValidationError(
                        row=0,
                        column=col,
                        value="",
                        error_type="missing_column",
                        message=f"Required column '{col}' is missing"
                    ))
            
            # Check for unexpected columns
            expected_columns = settings.CSV_REQUIRED_COLUMNS + settings.CSV_OPTIONAL_COLUMNS
            unexpected_columns = [col for col in csv_reader.fieldnames if col not in expected_columns]
            if unexpected_columns:
                warnings.append(f"Unexpected columns found: {', '.join(unexpected_columns)}")
            
            total_rows = 0
            valid_rows = 0
            invalid_rows = 0
            
            # Validate each row
            for row_num, row in enumerate(csv_reader, start=1):
                total_rows += 1
                row_valid = True
                
                # Skip completely empty rows
                if not any(row.values()):
                    warnings.append(f"Row {row_num}: Empty row skipped")
                    continue
                
                # Validate name
                name = row.get('name', '').strip()
                if not CSVProcessor._validate_name(name):
                    errors.append(ValidationError(
                        row=row_num,
                        column="name",
                        value=name,
                        error_type="invalid_name",
                        message="Name must be 2-255 characters long"
                    ))
                    row_valid = False
                
                # Validate address
                address = row.get('address', '').strip()
                if not CSVProcessor._validate_address(address):
                    errors.append(ValidationError(
                        row=row_num,
                        column="address",
                        value=address,
                        error_type="invalid_address",
                        message="Address must be 5-500 characters long"
                    ))
                    row_valid = False
                
                # Validate phone (optional)
                phone = row.get('phone', '').strip()
                if phone and not CSVProcessor._validate_phone_number(phone):
                    errors.append(ValidationError(
                        row=row_num,
                        column="phone",
                        value=phone,
                        error_type="invalid_phone",
                        message="Invalid phone number format"
                    ))
                    row_valid = False
                
                # Check for duplicate names in the same file
                if name and any(h.name.lower() == name.lower() for h in valid_hospitals):
                    warnings.append(f"Row {row_num}: Duplicate hospital name '{name}'")
                
                if row_valid and name and address:
                    valid_hospitals.append(HospitalCreate(
                        name=name,
                        address=address,
                        phone=phone if phone else None
                    ))
                    valid_rows += 1
                else:
                    invalid_rows += 1
            
            # Check file size constraints
            if valid_rows > settings.MAX_CSV_SIZE:
                errors.append(ValidationError(
                    row=0,
                    column="file",
                    value=str(valid_rows),
                    error_type="file_too_large",
                    message=f"File contains {valid_rows} valid hospitals. Maximum allowed is {settings.MAX_CSV_SIZE}"
                ))
            
            if valid_rows == 0 and total_rows > 0:
                errors.append(ValidationError(
                    row=0,
                    column="file",
                    value="",
                    error_type="no_valid_data",
                    message="No valid hospital records found in CSV"
                ))
            
            # Determine if validation passed
            is_valid = len(errors) == 0 and valid_rows > 0 and valid_rows <= settings.MAX_CSV_SIZE
            
            # Return preview (first 5 hospitals)
            preview_hospitals = valid_hospitals[:5]
            
            return CSVValidationResult(
                is_valid=is_valid,
                total_rows=total_rows,
                valid_rows=valid_rows,
                invalid_rows=invalid_rows,
                errors=errors,
                warnings=warnings,
                preview_hospitals=preview_hospitals,
                file_info=file_info
            )
            
        except UnicodeDecodeError:
            errors.append(ValidationError(
                row=0,
                column="file",
                value="",
                error_type="encoding_error",
                message="Invalid CSV file encoding. Please use UTF-8"
            ))
        except csv.Error as e:
            errors.append(ValidationError(
                row=0,
                column="file",
                value="",
                error_type="csv_error",
                message=f"CSV parsing error: {str(e)}"
            ))
        except Exception as e:
            errors.append(ValidationError(
                row=0,
                column="file",
                value="",
                error_type="unknown_error",
                message=f"Error processing CSV: {str(e)}"
            ))
        
        return CSVValidationResult(
            is_valid=False,
            total_rows=0,
            valid_rows=0,
            invalid_rows=0,
            errors=errors,
            warnings=warnings,
            preview_hospitals=[],
            file_info=file_info
        )
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