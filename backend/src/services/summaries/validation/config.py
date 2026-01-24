"""
Configuration for validation pipeline components.
All thresholds and settings are centralized here for easy modification.
"""

# Readability Configuration
READABILITY_MAX_GRADE_LEVEL = 8.0  # Target: 6th-8th grade reading level

# Safety Filter Configuration
SAFETY_BANNED_KEYWORDS = [
    "call 911",
    "emergency",
    "you must",
    "you should",
    "you need to",
    "immediately",
    "urgent",
    "critical",
    "life-threatening",
    "seek immediate",
    "go to the emergency room",
    "go to the ER",
]

SAFETY_MEDICAL_ADVICE_PATTERNS = [
    r"you (must|should|need to|have to)",
    r"(take|use|prescribe|recommend) (medication|drug|medicine)",
    r"you (can|cannot|should not) (eat|drink|exercise)",
]

SAFETY_ALARMIST_PATTERNS = [
    r"very (serious|dangerous|severe|critical)",
    r"extremely (worrisome|concerning|serious)",
    r"immediate (action|attention|treatment)",
]

# Entity Matching Configuration
ENTITY_FUZZY_MATCH_THRESHOLD = 80  # Percentage similarity for fuzzy matching (0-100)
ENTITY_CASE_SENSITIVE = False  # Whether entity matching is case-sensitive

# Self-Correction Loop Configuration
MAX_RETRY_ATTEMPTS = 3  # Maximum number of refinement attempts

# Component Configuration
ENABLE_FIDELITY_CHECK = True
ENABLE_HALLUCINATION_CHECK = True
ENABLE_READABILITY_CHECK = True
ENABLE_SAFETY_CHECK = True
