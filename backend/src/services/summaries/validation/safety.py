"""
Safety Component - Check D: Safety Filter
Scans for banned keywords, medical advice patterns, and alarmist language.
"""
import re
from typing import List
from services.summaries.validation.base import PipelineComponent
from schemas.validation import ValidationInput, ValidationResult
from services.summaries.validation.config import (
    SAFETY_BANNED_KEYWORDS,
    SAFETY_MEDICAL_ADVICE_PATTERNS,
    SAFETY_ALARMIST_PATTERNS,
)


class SafetyComponent(PipelineComponent):
    """
    Validates that the summary does not contain:
    - Banned keywords/phrases
    - Medical advice patterns
    - Alarmist language
    """
    
    def __init__(self):
        self.component_name = "SafetyCheck"
        # Compile regex patterns for efficiency
        self.medical_advice_regex = [re.compile(pattern, re.IGNORECASE) for pattern in SAFETY_MEDICAL_ADVICE_PATTERNS]
        self.alarmist_regex = [re.compile(pattern, re.IGNORECASE) for pattern in SAFETY_ALARMIST_PATTERNS]
    
    def _check_banned_keywords(self, text: str) -> List[str]:
        """Check for banned keywords (case-insensitive)."""
        text_lower = text.lower()
        found_keywords = []
        for keyword in SAFETY_BANNED_KEYWORDS:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)
        return found_keywords
    
    def _check_patterns(self, text: str, patterns: List[re.Pattern], pattern_type: str) -> List[str]:
        """Check for regex patterns and return matches."""
        matches = []
        for pattern in patterns:
            found = pattern.findall(text)
            if found:
                matches.extend([f"{pattern_type}: {match}" for match in found[:3]])  # Limit to first 3 matches per pattern
        return matches
    
    def process(self, input: ValidationInput) -> ValidationInput:
        """
        Scan summary for safety violations.
        Returns ValidationInput with validation result attached.
        """
        summary_text = input.draft_summary
        
        # Check for banned keywords
        banned_found = self._check_banned_keywords(summary_text)
        
        # Check for medical advice patterns
        medical_advice_found = self._check_patterns(summary_text, self.medical_advice_regex, "Medical advice")
        
        # Check for alarmist language
        alarmist_found = self._check_patterns(summary_text, self.alarmist_regex, "Alarmist language")
        
        # Combine all violations
        all_violations = banned_found + medical_advice_found + alarmist_found
        
        # Create validation result
        passed = len(all_violations) == 0
        error_messages = []
        
        if not passed:
            if banned_found:
                error_messages.append(f"Found banned keywords: {', '.join(banned_found[:3])}")
            if medical_advice_found:
                error_messages.append(f"Found medical advice patterns: {len(medical_advice_found)} instances")
            if alarmist_found:
                error_messages.append(f"Found alarmist language: {len(alarmist_found)} instances")
        
        validation_result = ValidationResult(
            component_name=self.component_name,
            passed=passed,
            error_messages=error_messages,
            metadata={
                "violation_count": len(all_violations),
                "banned_keywords_found": banned_found,
                "medical_advice_found": medical_advice_found,
                "alarmist_language_found": alarmist_found,
                "all_violations": all_violations[:10],  # Limit to first 10 for metadata
            }
        )
        
        # Attach result to input
        if not hasattr(input, '_validation_results'):
            input._validation_results = []
        input._validation_results.append(validation_result)
        
        return input
