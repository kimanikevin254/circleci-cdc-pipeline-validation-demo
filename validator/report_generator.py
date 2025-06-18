"""Report generation utilities."""

import os
from datetime import datetime
from typing import List
from models import TestResult, ValidationResult

class ReportGenerator:
    @staticmethod
    def generate_report(test_results: List[TestResult]) -> str:
        """Generate a comprehensive test report."""
        total_tests = len(test_results)
        passed_tests = len([r for r in test_results if r.result == ValidationResult.PASS])
        failed_tests = len([r for r in test_results if r.result == ValidationResult.FAIL])
        
        report = f"""
CDC PIPELINE VALIDATION REPORT
===========================
Generated: {datetime.now()}

SUMMARY:
--------
Total Tests: {total_tests}
Passed: {passed_tests}
Failed: {failed_tests}
Success Rate: {(passed_tests/total_tests)*100:.1f}%

DETAILED RESULTS:
-----------------
"""
                
        for result in test_results:
            report += f"""
Test: {result.test_name}
Status: {result.result.value}
Details: {result.details}
Timestamp: {result.timestamp}
Metrics: {result.metrics or 'N/A'}
{'='*100}
"""

        return report
    
    @staticmethod
    def save_report(report: str, filename: str = None) -> str:
        """Save report to file."""
        if not filename:
            filename = f"reports/validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, "w") as f:
            f.write(report)
        
        return filename