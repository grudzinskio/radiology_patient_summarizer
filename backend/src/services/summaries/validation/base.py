# Abstract base class for pipeline components
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class PipelineComponent(ABC):
    """
    Abstract base class for pipeline components
    """
    @abstractmethod
    def process(self, input: Any) -> Any:
        """
        Process the input and return the output
        """
        raise NotImplementedError("Subclasses must implement this method")