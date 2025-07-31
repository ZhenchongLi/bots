from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import httpx
import orjson as json
import structlog
from src.config.settings import PlatformType

logger = structlog.get_logger()


class BasePlatformClient(ABC):
    """Base class for platform-specific API clients."""
    
    def __init__(self, platform_config: Dict[str, Any]):
        self.config = platform_config
        self.api_key = platform_config.get("api_key")
        self.base_url = platform_config.get("base_url")
        self.timeout = platform_config.get("timeout", 300)
        self.default_headers = platform_config.get("default_headers", {})
    
    @abstractmethod
    async def make_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make a request to the platform API."""
        pass
    
    async def make_stream_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ):
        """Make a streaming request to the platform API. Default implementation for non-streaming clients."""
        # Fallback: make regular request for clients that don't override this method
        response = await self.make_request(method, path, headers, json_data, params)
        if response.get("json"):
            yield f"data: {json.dumps(response['json']).decode()}"
    
    def prepare_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Prepare headers for the request."""
        request_headers = self.default_headers.copy()
        if headers:
            # Filter out potentially conflicting headers
            filtered_headers = {k: v for k, v in headers.items() 
                              if k.lower() not in ['authorization', 'host', 'content-length']}
            request_headers.update(filtered_headers)
        return request_headers


class OpenAIClient(BasePlatformClient):
    """OpenAI API client."""
    
    async def make_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}{path}"
        
        request_headers = self.prepare_headers(headers)
        request_headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=request_headers,
                json=json_data,
                params=params,
                timeout=self.timeout,
            )
            
            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": response.content,
                "json": response.json() if self._is_json_response(response) else None,
            }
    
    def _is_json_response(self, response) -> bool:
        """Check if response is JSON."""
        content_type = response.headers.get("content-type", "")
        return content_type.startswith("application/json")
    
    async def make_stream_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ):
        """Make a streaming request to the platform API."""
        url = f"{self.base_url.rstrip('/')}{path}"
        
        request_headers = self.prepare_headers(headers)
        request_headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                method=method,
                url=url,
                headers=request_headers,
                json=json_data,
                params=params,
                timeout=self.timeout,
            ) as response:
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        yield chunk


class AnthropicClient(BasePlatformClient):
    """Anthropic (Claude) API client."""
    
    async def make_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}{path}"
        
        # Convert OpenAI format to Anthropic format
        if json_data:
            json_data = self._convert_to_anthropic_format(json_data)
        
        request_headers = self.prepare_headers(headers)
        request_headers.update({
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        })
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=request_headers,
                json=json_data,
                params=params,
                timeout=self.timeout,
            )
            
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": response.content,
                "json": response.json() if self._is_json_response(response) else None,
            }
            
            # Convert Anthropic response back to OpenAI format
            if result["json"]:
                result["json"] = self._convert_from_anthropic_format(result["json"])
            
            return result
    
    def _convert_to_anthropic_format(self, openai_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert OpenAI request format to Anthropic format."""
        if "messages" in openai_data:
            # Convert messages format
            anthropic_data = openai_data.copy()
            messages = anthropic_data["messages"]
            
            # Extract system message if present
            system_message = None
            filtered_messages = []
            
            for msg in messages:
                if msg.get("role") == "system":
                    system_message = msg.get("content", "")
                else:
                    filtered_messages.append(msg)
            
            anthropic_data["messages"] = filtered_messages
            if system_message:
                anthropic_data["system"] = system_message
            
            # Map other parameters
            if "max_tokens" not in anthropic_data:
                anthropic_data["max_tokens"] = 4096
                
        return anthropic_data
    
    def _convert_from_anthropic_format(self, anthropic_response: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Anthropic response format to OpenAI format."""
        if "content" in anthropic_response and isinstance(anthropic_response["content"], list):
            # Convert Claude response to OpenAI format
            content = anthropic_response["content"][0].get("text", "") if anthropic_response["content"] else ""
            
            return {
                "id": anthropic_response.get("id", ""),
                "object": "chat.completion",
                "created": 1677652288,  # Placeholder timestamp
                "model": anthropic_response.get("model", ""),
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": anthropic_response.get("stop_reason", "stop")
                }],
                "usage": {
                    "prompt_tokens": anthropic_response.get("usage", {}).get("input_tokens", 0),
                    "completion_tokens": anthropic_response.get("usage", {}).get("output_tokens", 0),
                    "total_tokens": anthropic_response.get("usage", {}).get("input_tokens", 0) + 
                                  anthropic_response.get("usage", {}).get("output_tokens", 0)
                }
            }
        
        return anthropic_response
    
    def _is_json_response(self, response) -> bool:
        """Check if response is JSON."""
        content_type = response.headers.get("content-type", "")
        return content_type.startswith("application/json")
    
    async def make_stream_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ):
        """Make a streaming request to the platform API."""
        url = f"{self.base_url.rstrip('/')}{path}"
        
        # Convert OpenAI format to Anthropic format for streaming
        if json_data:
            json_data = self._convert_to_anthropic_format(json_data)
        
        request_headers = self.prepare_headers(headers)
        request_headers.update({
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        })
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                method=method,
                url=url,
                headers=request_headers,
                json=json_data,
                params=params,
                timeout=self.timeout,
            ) as response:
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        yield chunk


class GoogleClient(BasePlatformClient):
    """Google (Gemini) API client."""
    
    async def make_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        # Google uses API key in URL params
        url = f"{self.base_url.rstrip('/')}{path}"
        
        if not params:
            params = {}
        params["key"] = self.api_key
        
        # Convert OpenAI format to Google format
        if json_data:
            json_data = self._convert_to_google_format(json_data)
        
        request_headers = self.prepare_headers(headers)
        request_headers.update({
            "Content-Type": "application/json",
        })
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=request_headers,
                json=json_data,
                params=params,
                timeout=self.timeout,
            )
            
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": response.content,
                "json": response.json() if self._is_json_response(response) else None,
            }
            
            # Convert Google response back to OpenAI format
            if result["json"]:
                result["json"] = self._convert_from_google_format(result["json"])
            
            return result
    
    def _convert_to_google_format(self, openai_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert OpenAI request format to Google format."""
        if "messages" in openai_data:
            google_data = {
                "contents": []
            }
            
            for msg in openai_data["messages"]:
                role = "user" if msg.get("role") == "user" else "model"
                google_data["contents"].append({
                    "role": role,
                    "parts": [{"text": msg.get("content", "")}]
                })
            
            # Add generation config
            if "max_tokens" in openai_data:
                google_data["generationConfig"] = {
                    "maxOutputTokens": openai_data["max_tokens"]
                }
            
            return google_data
        
        return openai_data
    
    def _convert_from_google_format(self, google_response: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Google response format to OpenAI format."""
        if "candidates" in google_response:
            candidate = google_response["candidates"][0] if google_response["candidates"] else {}
            content = candidate.get("content", {}).get("parts", [{}])[0].get("text", "")
            
            return {
                "id": "google-" + str(hash(content))[:8],
                "object": "chat.completion",
                "created": 1677652288,  # Placeholder timestamp
                "model": "gemini-pro",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": candidate.get("finishReason", "STOP").lower()
                }],
                "usage": {
                    "prompt_tokens": google_response.get("usageMetadata", {}).get("promptTokenCount", 0),
                    "completion_tokens": google_response.get("usageMetadata", {}).get("candidatesTokenCount", 0),
                    "total_tokens": google_response.get("usageMetadata", {}).get("totalTokenCount", 0)
                }
            }
        
        return google_response
    
    def _is_json_response(self, response) -> bool:
        """Check if response is JSON."""
        content_type = response.headers.get("content-type", "")
        return content_type.startswith("application/json")




class PlatformClientFactory:
    """Factory for creating platform-specific clients."""
    
    _clients = {
        PlatformType.OPENAI: OpenAIClient,
        PlatformType.AZURE_OPENAI: OpenAIClient,  # Azure OpenAI uses same format as OpenAI
        PlatformType.ANTHROPIC: AnthropicClient,
        PlatformType.GOOGLE: GoogleClient,
    }
    
    @classmethod
    def create_client(cls, platform_type: str, platform_config: Dict[str, Any]) -> BasePlatformClient:
        """Create a client for the specified platform type."""
        # Try adapter system first for supported platforms
        try:
            from src.adapters.proxy import AdapterProxy
            from src.adapters.manager import adapter_manager
            
            if adapter_manager.is_platform_supported(platform_type):
                logger.info("Using adapter system for platform", platform=platform_type)
                return AdapterProxy(platform_config)
        except ImportError:
            logger.warning("Adapter system not available, using legacy clients")
        except Exception as e:
            logger.warning("Failed to use adapter system, falling back to legacy", 
                          platform=platform_type, error=str(e))
        
        # Fallback to legacy clients
        client_class = cls._clients.get(platform_type)
        if not client_class:
            # Default to OpenAI client for custom platforms
            client_class = OpenAIClient
        
        return client_class(platform_config)