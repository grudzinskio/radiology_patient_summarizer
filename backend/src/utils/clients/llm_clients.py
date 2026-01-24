from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Type, TypeVar
from openai import OpenAI
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from openai import AsyncOpenAI

load_dotenv()

T = TypeVar('T', bound=BaseModel)

class BaseLLMClient(ABC):
    """
    Base class for all LLM clients, works for all OpenAI-compatible clients
    """
    def __init__(self):
        self.client = None
        self.model = None
    
    @abstractmethod
    def _initialize_client(self):
        """Override this to set up self.client and self.model"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def generate(self, messages: List[Dict], **kwargs) -> str:
        """
        Standard generation
        """
        if self.client is None:
            self._initialize_client()

        model = kwargs.pop("model", self.model)
        response = self.client.chat.completions.create(model=model, messages=messages, **kwargs)
        return response.choices[0].message.content
    
    def generate_stream(self, messages: List[Dict], **kwargs):
        """
        Streaming generation
        """
        if self.client is None:
            self._initialize_client()

        model = kwargs.pop("model", self.model)
        stream = self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            **kwargs,
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def generate_parsed(self, messages: List[Dict], schema: Type[T], **kwargs) -> T:
        """
        Generate a parsed response using structured outputs.
        
        Args:
            messages: The messages to send to the LLM
            schema: The Pydantic model class to parse the response into
            **kwargs: Additional arguments to pass to the LLM
            
        Returns:
            The parsed response as an instance of the schema
        """
        if self.client is None:
            self._initialize_client()
        
        # Use the beta parse endpoint for structured outputs
        model = kwargs.pop("model", self.model)
        response = self.client.beta.chat.completions.parse(
            model=model, 
            messages=messages, 
            response_format=schema,  # Pass the class, not an instance
            **kwargs
        )
        return response.choices[0].message.parsed


class AsyncBaseLLMClient(ABC):
    """
    Base class for async LLM clients
    """
    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self.model: Optional[str] = None
    
    @abstractmethod
    def _initialize_client(self):
        """Override this to set up self.client and self.model"""
        raise NotImplementedError("Subclasses must implement this method")
    
    async def generate(self, messages: List[Dict], **kwargs) -> str:
        """Standard async generation"""
        if self.client is None:
            self._initialize_client()

        model = kwargs.pop("model", self.model)
        response = await self.client.chat.completions.create(
            model=model, 
            messages=messages, 
            **kwargs
        )
        return response.choices[0].message.content

    async def generate_parsed(self, messages: List[Dict], schema: Type[T], **kwargs) -> T:
        """Generate a parsed response using structured outputs."""
        if self.client is None:
            self._initialize_client()
        
        model = kwargs.pop("model", self.model)
        response = await self.client.beta.chat.completions.parse(
            model=model, 
            messages=messages, 
            response_format=schema,
            **kwargs
        )
        return response.choices[0].message.parsed


class OpenAIClient(BaseLLMClient):
    """
    Client for OpenAI
    """
    def _initialize_client(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "Missing OPENAI_API_KEY. Set it in your environment or .env file."
            )
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-5-mini"

class AsyncOpenAIClient(AsyncBaseLLMClient):
    """
    Client for OpenAI async
    """
    def _initialize_client(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "Missing OPENAI_API_KEY. Set it in your environment or .env file."
            )
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-5-mini"


class RosieLlamaClient(BaseLLMClient):
    """
    Client for Rosie's Llama model
    """
    def _initialize_client(self):
        self.client = OpenAI(
            base_url="http://dh-dgxh100-2.hpc.msoe.edu:8000/v1",
            api_key="not_used"
        )
        self.model = "meta/llama-3.3-70b-instruct"