"""
API client for communicating with the backend
"""
import httpx
from flask import current_app, session
from typing import Dict, Any, Optional


class APIClient:
    """Client for interacting with the backend API"""
    
    def __init__(self):
        self.base_url = current_app.config['BACKEND_API_URL']
        self.api_prefix = current_app.config['API_V1_STR']
        self.timeout = 10.0  # seconds
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers including auth token if available"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Add auth token if available
        token = session.get('access_token')
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        return headers
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make GET request to API"""
        url = f"{self.base_url}{self.api_prefix}{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                url,
                params=params,
                headers=self._get_headers()
            )
            
            response.raise_for_status()
            return response.json()
    
    async def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make POST request to API"""
        url = f"{self.base_url}{self.api_prefix}{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                json=data,
                headers=self._get_headers()
            )
            
            response.raise_for_status()
            return response.json()
    
    async def put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make PUT request to API"""
        url = f"{self.base_url}{self.api_prefix}{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.put(
                url,
                json=data,
                headers=self._get_headers()
            )
            
            response.raise_for_status()
            return response.json()
    
    async def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make DELETE request to API"""
        url = f"{self.base_url}{self.api_prefix}{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.delete(
                url,
                headers=self._get_headers()
            )
            
            response.raise_for_status()
            return response.json()
    
    # Auth-specific methods
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """Login user and get access token"""
        # Supabase auth endpoint uses JSON data with email/password
        url = f"{self.base_url}{self.api_prefix}/auth/login"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                json={
                    "email": email,
                    "password": password
                },
                headers=self._get_headers()
            )

            response.raise_for_status()
            return response.json()
    
    async def register(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new user"""
        return await self.post("/auth/register", user_data)
    
    async def verify_email(self, token: str) -> Dict[str, Any]:
        """Verify user email"""
        return await self.post("/auth/verify-email", {"token": token})
