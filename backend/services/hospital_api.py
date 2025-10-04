import httpx
from typing import List, Optional
from config import settings
from models import HospitalCreate, HospitalResponse

class HospitalAPIService:
    def __init__(self):
        self.base_url = settings.HOSPITAL_API_BASE_URL
        # Optimize client for concurrent requests
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
        timeout = httpx.Timeout(
            settings.HTTP_TIMEOUT_SECONDS, 
            connect=settings.HTTP_CONNECT_TIMEOUT_SECONDS
        )
        self.client = httpx.AsyncClient(
            timeout=timeout,
            limits=limits
        )
    
    async def create_hospital(self, hospital: HospitalCreate, batch_id: str) -> Optional[HospitalResponse]:
        """Create a single hospital via the external API"""
        try:
            data = {
                "name": hospital.name,
                "address": hospital.address,
                "creation_batch_id": batch_id
            }
            if hospital.phone:
                data["phone"] = hospital.phone
                
            response = await self.client.post(
                f"{self.base_url}/hospitals/",
                json=data
            )
            response.raise_for_status()
            return HospitalResponse(**response.json())
        except Exception as e:
            print(f"Error creating hospital: {e}")
            return None
    
    async def activate_batch(self, batch_id: str) -> bool:
        """Activate all hospitals in a batch"""
        try:
            response = await self.client.patch(
                f"{self.base_url}/hospitals/batch/{batch_id}/activate"
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error activating batch {batch_id}: {e}")
            return False
    
    async def get_batch_hospitals(self, batch_id: str) -> List[HospitalResponse]:
        """Get all hospitals in a batch"""
        try:
            response = await self.client.get(
                f"{self.base_url}/hospitals/batch/{batch_id}"
            )
            response.raise_for_status()
            return [HospitalResponse(**hospital) for hospital in response.json()]
        except Exception as e:
            print(f"Error getting batch hospitals: {e}")
            return []
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()