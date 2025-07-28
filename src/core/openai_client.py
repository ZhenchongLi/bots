import httpx
from typing import Dict, Any, Optional
from src.config.settings import settings


class OpenAIClient:
    def __init__(self):
        self.base_url = settings.openai_base_url.rstrip('/')
        self.api_key = settings.openai_api_key
        
    async def proxy_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        
        # Prepare headers
        proxy_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        if headers:
            # Remove authorization from original headers to avoid conflicts
            filtered_headers = {k: v for k, v in headers.items() 
                             if k.lower() not in ['authorization', 'host']}
            proxy_headers.update(filtered_headers)
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=proxy_headers,
                json=json_data,
                params=params,
                timeout=300.0,  # 5 minute timeout for long requests
            )
            
            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": response.content,
                "json": response.json() if response.headers.get("content-type", "").startswith("application/json") else None,
            }