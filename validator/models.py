"""Data models and enums"""

from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any

class ValidationResult(Enum):
    PASS = "PASS"
    FAIL = "FAIL"

@dataclass
class TestResult:
    test_name: str
    result: ValidationResult
    details: str
    timestamp: datetime
    metrics: Dict[str, Any] = None