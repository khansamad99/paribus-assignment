import time
import json
import os
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field, asdict
from threading import Lock
from pathlib import Path

class ProcessingStatus(str, Enum):
    INITIALIZING = "initializing"
    VALIDATING = "validating"
    PROCESSING = "processing"
    ACTIVATING = "activating"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    RESUMABLE = "resumable"

@dataclass
class HospitalProgress:
    row: int
    name: str
    status: str = "pending"  # pending, processing, completed, failed
    hospital_id: Optional[int] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None

@dataclass
class BatchProgress:
    batch_id: str
    status: ProcessingStatus = ProcessingStatus.INITIALIZING
    total_hospitals: int = 0
    processed_hospitals: int = 0
    failed_hospitals: int = 0
    start_time: float = field(default_factory=time.time)
    completion_time: Optional[float] = None
    hospitals: List[HospitalProgress] = field(default_factory=list)
    current_step: str = "Starting processing..."
    batch_activated: bool = False
    
    # Resume capability fields
    is_resumable: bool = False
    resume_from_row: int = 0
    original_csv_data: List[Dict[str, Any]] = field(default_factory=list)
    failure_reason: Optional[str] = None
    resume_count: int = 0
    last_checkpoint_time: Optional[float] = None
    
    @property
    def processing_time_seconds(self) -> float:
        if self.completion_time:
            return self.completion_time - self.start_time
        return time.time() - self.start_time
    
    @property
    def progress_percentage(self) -> float:
        if self.total_hospitals == 0:
            return 0.0
        return (self.processed_hospitals + self.failed_hospitals) / self.total_hospitals * 100

class ProgressTracker:
    def __init__(self):
        self._progress_store: Dict[str, BatchProgress] = {}
        self._lock = Lock()
        self._storage_dir = Path("batch_storage")
        self._storage_dir.mkdir(exist_ok=True)
    
    def create_batch_progress(self, batch_id: str, total_hospitals: int, hospital_names: List[str]) -> BatchProgress:
        """Initialize progress tracking for a new batch"""
        with self._lock:
            hospitals = [
                HospitalProgress(row=i+1, name=name) 
                for i, name in enumerate(hospital_names)
            ]
            
            progress = BatchProgress(
                batch_id=batch_id,
                total_hospitals=total_hospitals,
                hospitals=hospitals,
                current_step="Initialized batch processing"
            )
            
            self._progress_store[batch_id] = progress
            return progress
    
    def update_status(self, batch_id: str, status: ProcessingStatus, step: str = None):
        """Update the overall batch status"""
        with self._lock:
            if batch_id in self._progress_store:
                self._progress_store[batch_id].status = status
                if step:
                    self._progress_store[batch_id].current_step = step
    
    def update_hospital_progress(self, batch_id: str, row: int, status: str, 
                               hospital_id: Optional[int] = None, 
                               error_message: Optional[str] = None,
                               processing_time: Optional[float] = None):
        """Update progress for a specific hospital"""
        with self._lock:
            if batch_id not in self._progress_store:
                return
            
            progress = self._progress_store[batch_id]
            
            # Find and update the hospital
            for hospital in progress.hospitals:
                if hospital.row == row:
                    hospital.status = status
                    hospital.hospital_id = hospital_id
                    hospital.error_message = error_message
                    hospital.processing_time = processing_time
                    break
            
            # Update counters
            progress.processed_hospitals = sum(
                1 for h in progress.hospitals 
                if h.status in ["completed", "created", "created_and_activated"]
            )
            progress.failed_hospitals = sum(
                1 for h in progress.hospitals if h.status == "failed"
            )
    
    def complete_batch(self, batch_id: str, batch_activated: bool = False):
        """Mark batch as completed"""
        with self._lock:
            if batch_id in self._progress_store:
                progress = self._progress_store[batch_id]
                progress.status = ProcessingStatus.COMPLETED
                progress.completion_time = time.time()
                progress.batch_activated = batch_activated
                progress.current_step = "Batch processing completed"
                
                # Update hospital statuses if batch was activated
                if batch_activated:
                    for hospital in progress.hospitals:
                        if hospital.status in ["completed", "created"]:
                            hospital.status = "created_and_activated"
    
    def mark_batch_failed(self, batch_id: str, error: str):
        """Mark batch as failed"""
        with self._lock:
            if batch_id in self._progress_store:
                progress = self._progress_store[batch_id]
                progress.status = ProcessingStatus.FAILED
                progress.completion_time = time.time()
                progress.current_step = f"Processing failed: {error}"
    
    def get_progress(self, batch_id: str) -> Optional[BatchProgress]:
        """Get current progress for a batch"""
        with self._lock:
            return self._progress_store.get(batch_id)
    
    def _save_batch_to_disk(self, batch_progress: BatchProgress):
        """Save batch progress to disk for persistence"""
        try:
            file_path = self._storage_dir / f"{batch_progress.batch_id}.json"
            
            # Convert dataclass to dict for JSON serialization
            data = asdict(batch_progress)
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Failed to save batch to disk: {e}")
    
    def _load_batch_from_disk(self, batch_id: str) -> Optional[BatchProgress]:
        """Load batch progress from disk"""
        try:
            file_path = self._storage_dir / f"{batch_id}.json"
            
            if not file_path.exists():
                return None
                
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Convert back to dataclass
            hospitals = [HospitalProgress(**h) for h in data.get('hospitals', [])]
            data['hospitals'] = hospitals
            data['status'] = ProcessingStatus(data['status'])
            
            return BatchProgress(**data)
            
        except Exception as e:
            print(f"Warning: Failed to load batch from disk: {e}")
            return None
    
    def _delete_batch_from_disk(self, batch_id: str):
        """Delete batch file from disk"""
        try:
            file_path = self._storage_dir / f"{batch_id}.json"
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            print(f"Warning: Failed to delete batch file: {e}")
    
    def mark_batch_resumable(self, batch_id: str, failure_reason: str, csv_data: List[Dict]):
        """Mark a batch as resumable after failure"""
        with self._lock:
            if batch_id in self._progress_store:
                progress = self._progress_store[batch_id]
                progress.status = ProcessingStatus.RESUMABLE
                progress.is_resumable = True
                progress.failure_reason = failure_reason
                progress.original_csv_data = csv_data
                progress.last_checkpoint_time = time.time()
                
                # Find the next row to resume from
                completed_rows = [h.row for h in progress.hospitals if h.status in ["created", "created_and_activated"]]
                progress.resume_from_row = max(completed_rows, default=0) + 1 if completed_rows else 1
                
                # Save to disk
                self._save_batch_to_disk(progress)
    
    def get_resumable_batches(self) -> List[Dict]:
        """Get all resumable batches"""
        resumable = []
        
        # Check in-memory store
        with self._lock:
            for progress in self._progress_store.values():
                if progress.is_resumable and progress.status == ProcessingStatus.RESUMABLE:
                    resumable.append({
                        "batch_id": progress.batch_id,
                        "total_hospitals": progress.total_hospitals,
                        "processed_hospitals": progress.processed_hospitals,
                        "failed_hospitals": progress.failed_hospitals,
                        "resume_from_row": progress.resume_from_row,
                        "failure_reason": progress.failure_reason,
                        "last_checkpoint_time": progress.last_checkpoint_time
                    })
        
        # Check disk storage for batches not in memory
        try:
            for file_path in self._storage_dir.glob("*.json"):
                batch_id = file_path.stem
                if batch_id not in self._progress_store:
                    progress = self._load_batch_from_disk(batch_id)
                    if progress and progress.is_resumable and progress.status == ProcessingStatus.RESUMABLE:
                        resumable.append({
                            "batch_id": progress.batch_id,
                            "total_hospitals": progress.total_hospitals,
                            "processed_hospitals": progress.processed_hospitals,
                            "failed_hospitals": progress.failed_hospitals,
                            "resume_from_row": progress.resume_from_row,
                            "failure_reason": progress.failure_reason,
                            "last_checkpoint_time": progress.last_checkpoint_time
                        })
        except Exception as e:
            print(f"Warning: Error reading resumable batches from disk: {e}")
        
        return resumable
    
    def load_batch_for_resume(self, batch_id: str) -> Optional[BatchProgress]:
        """Load a batch for resume operation"""
        with self._lock:
            # Check in-memory first
            if batch_id in self._progress_store:
                return self._progress_store[batch_id]
            
            # Load from disk
            progress = self._load_batch_from_disk(batch_id)
            if progress:
                self._progress_store[batch_id] = progress
            
            return progress
    
    def save_checkpoint(self, batch_id: str):
        """Save a checkpoint for the batch"""
        with self._lock:
            if batch_id in self._progress_store:
                progress = self._progress_store[batch_id]
                progress.last_checkpoint_time = time.time()
                self._save_batch_to_disk(progress)

    def cleanup_old_batches(self, max_age_hours: int = None):
        """Remove old batch progress data"""
        from config import settings
        if max_age_hours is None:
            max_age_hours = settings.PROGRESS_CLEANUP_HOURS
            
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        with self._lock:
            expired_batches = [
                batch_id for batch_id, progress in self._progress_store.items()
                if current_time - progress.start_time > max_age_seconds
            ]
            
            for batch_id in expired_batches:
                del self._progress_store[batch_id]
                self._delete_batch_from_disk(batch_id)
            
            return len(expired_batches)

# Global progress tracker instance
progress_tracker = ProgressTracker()