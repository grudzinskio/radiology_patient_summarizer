from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

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

        response = self.client.chat.completions.create(model=self.model, messages=messages, **kwargs)
        return response.choices[0].message.content
    
    def generate_stream(self, messages: List[Dict], **kwargs):
        """
        Streaming generation
        """
        if self.client is None:
            self._initialize_client()

        stream = self.client.chat.completions.create(model=self.model, messages=messages, stream=True, **kwargs)
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


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