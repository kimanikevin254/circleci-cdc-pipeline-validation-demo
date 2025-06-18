"""Main validator orchestrator"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any

from config import PIPELINE_SYNC_WAIT_TIME_SECS
from models import TestResult, ValidationResult
from data_access import DataAccessManager
from test_data_generator import TestDataGenerator
from validators import DataValidator
from report_generator import ReportGenerator

class CDCPipelineValidator:
    def __init__(self, postgres_config: Dict[str, Any], s3_config: Dict[str, Any], table_configs: List[Dict[str, Any]]):
        self.table_configs = {config['table_name']: config for config in table_configs}
        self.test_results: List[TestResult] = []

        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.data_access = DataAccessManager(postgres_config, s3_config)
        self.test_data_generator = TestDataGenerator()
        self.validator = DataValidator(self.data_access, self.table_configs)
        self.report_generator = ReportGenerator()

    def run_baseline_validation(self) -> List[TestResult]:
        """Run baseline validation for all configured tables."""
        self.logger.info("Starting baseline validation...")
        results = []

        for table_name in self.table_configs.keys():
            self.logger.info(f"Validating table: {table_name}")

            # Row Count Validation
            row_count_result = self.validator.validate_row_counts(table_name)
            results.append(row_count_result)

            # Data Integrity Validation
            data_integrity_result = self.validator.validate_data_integrity(table_name)
            results.append(data_integrity_result)

        self.test_results.extend(results)
        return results

    def run_change_validation_test(self, table_name: str, test_changes: List[Dict[str, Any]]) -> List[TestResult]:
        """Run complete change validation test."""
        results = []

        try:
            # Make controlled changes
            self.logger.info(f"Creating test changes for table: {table_name}")
            self.data_access.execute_changes(table_name, test_changes)

            # Wait for pipeline sync
            self.logger.info(f"Pausing for {PIPELINE_SYNC_WAIT_TIME_SECS} seconds for data to sync...")
            time.sleep(PIPELINE_SYNC_WAIT_TIME_SECS)

            # Validate changes propagated
            change_result = self.validator.validate_changes_propagated(table_name, test_changes)
            results.append(change_result)

            self.logger.info(f"Change validation completed for {table_name}")

        except Exception as e:
            error_result = TestResult(
                test_name=f"change_validation_test_{table_name}",
                result=ValidationResult.FAIL,
                details=f"Test failed with error: {str(e)}",
                timestamp=datetime.now()
            )
            results.append(error_result)

        self.test_results.extend(results)
        return results

    def generate_test_changes(self, table_name: str) -> List[Dict[str, Any]]:
        """Generate test changes for a table."""
        test_changes = []
        primary_key = self.table_configs[table_name]['primary_key']

        # Generate an insert change
        insert_change = self.test_data_generator.generate_test_data(table_name, 'insert')
        if insert_change:
            test_changes.append(insert_change)

        # Get existing data for update/delete operations
        existing_data = self.data_access.get_postgres_data(table_name)

        if not existing_data.empty:
            # Generate an update change
            update_change = self.test_data_generator.generate_test_data(
                table_name, 'update', existing_data, primary_key
            )
            if update_change:
                test_changes.append(update_change)

            # Generate a delete change
            delete_change = self.test_data_generator.generate_test_data(
                table_name, 'delete', existing_data, primary_key
            )
            if delete_change:
                test_changes.append(delete_change)

        return test_changes

    def generate_report(self) -> str:
        """Generate a comprehensive test report."""
        return self.report_generator.generate_report(self.test_results)

    def save_report(self, filename: str = None) -> str:
        """Save report to file."""
        report = self.generate_report()
        return self.report_generator.save_report(report, filename)

    def cleanup(self):
        """Clean up connections."""
        self.data_access.close_pg_connection()
        self.logger.info("Connections closed")