"""Validation logic for the CDC pipeline"""

import re
import logging
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd

from models import TestResult, ValidationResult
from config import HUDI_RECORD_KEY, HUDI_DELETION_COLUMN

class DataValidator:
    def __init__(self, data_access_manager, table_configs: Dict[str, Dict]):
        self.data_access = data_access_manager
        self.table_configs = table_configs
        self.logging = logging.getLogger(__name__)

    def validate_row_counts(self, table_name: str) -> TestResult:
        """Validate that row counts match between PostgreSQL and S3."""
        try:
            pg_data = self.data_access.get_postgres_data(table_name)
            s3_data = self.data_access.get_s3_data(table_name)

            # Filter out soft-deleted rows from the datalake
            active_s3_data = s3_data[s3_data[HUDI_DELETION_COLUMN] != "true"]

            s3_count = len(active_s3_data)
            pg_count = len(pg_data)

            if pg_count == s3_count:
                result = ValidationResult.PASS
                details = f"Row counts match: {pg_count} rows."
            else:
                result = ValidationResult.FAIL
                details = f"Row counts do not match: PostgreSQL has {pg_count} rows, S3 has {s3_count} rows."

            return TestResult(
                test_name=f"row_count_validation_{table_name}",
                result=result,
                details=details,
                timestamp=datetime.now(),
                metrics={"pg_count": pg_count, "s3_count": s3_count}
            )

        except Exception as e:
            return TestResult(
                test_name=f"row_count_validation_{table_name}",
                result=ValidationResult.FAIL,
                details=str(e),
                timestamp=datetime.now()
            )

    def validate_data_integrity(self, table_name: str) -> TestResult:
        """Validate data integrity by comparing primary keys."""
        try:
            pg_data = self.data_access.get_postgres_data(table_name)
            s3_data = self.data_access.get_s3_data(table_name)

            if pg_data.empty and s3_data.empty:
                return TestResult(
                    test_name=f"data_integrity_validation_{table_name}",
                    result=ValidationResult.PASS,
                    details="Both datasets are empty.",
                    timestamp=datetime.now()
                )

            # Filter out deleted records from S3 data
            s3_data = s3_data[s3_data[HUDI_DELETION_COLUMN] != "true"]

            pg_pk_col = self.table_configs[table_name]['primary_key']

            if pg_pk_col in pg_data.columns and HUDI_RECORD_KEY in s3_data.columns:
                # Compare primary keys
                pg_ids = set(pg_data[pg_pk_col].astype(str))
                s3_ids = set(s3_data[HUDI_RECORD_KEY].astype(str))

                missing_in_s3 = pg_ids - s3_ids
                extra_in_s3 = s3_ids - pg_ids

                if len(missing_in_s3) == 0 and len(extra_in_s3) == 0:
                    result = ValidationResult.PASS
                    details = "Data integrity check passed. All primary keys match."
                else:
                    result = ValidationResult.FAIL
                    details = (
                        f"Data integrity check failed. "
                        f"Missing in S3: {len(missing_in_s3)} rows, "
                        f"Extra in S3: {len(extra_in_s3)} rows."
                    )
            else:
                result = ValidationResult.FAIL
                details = f"PG primary key or Hudi record key not found in the datasets."

            return TestResult(
                test_name=f"data_integrity_validation_{table_name}",
                result=result,
                details=details,
                timestamp=datetime.now()
            )

        except Exception as e:
            return TestResult(
                test_name=f"data_integrity_validation_{table_name}",
                result=ValidationResult.FAIL,
                details=str(e),
                timestamp=datetime.now()
            )
        
    def _extract_pk_from_where_clause(self, where_clause: str, pk_col: str) -> Any:
        """Extract primary key value from WHERE clause."""
        try:
            # Handle common WHERE clause formats
            # "id = 1", "id=1", "id = '1'", etc.
            pattern = rf"{pk_col}\s*=\s*['\"]?([^'\"\s]+)['\"]?"
            match = re.search(pattern, where_clause, re.IGNORECASE)

            if match:
                value = match.group(1)
                # Try to convert to int if possible
                try:
                    return int(value)
                except ValueError:
                    return value
            return None
        except Exception:
            return None

    def validate_changes_propagated(self, table_name: str, expected_changes: List[Dict[str, Any]]) -> TestResult:
        """Validate that controlled changes are reflected in the data lake."""
        try:
            s3_data = self.data_access.get_s3_data(table_name)
            pk_col = self.table_configs[table_name]['primary_key']

            changes_validated = 0
            failed_validations = []

            for change in expected_changes:
                if change['operation'] == 'insert':
                    # Check if the inserted record exists in the datalake
                    inserted_data = change['data']

                    # Find matching rows by filtering on all inserted fields (excluding the PK)
                    matching_condition = True
                    filter_fields = {}

                    for key, expected_value in inserted_data.items():
                        if key != pk_col and key in s3_data.columns:
                            filter_fields[key] = expected_value
                            matching_condition = matching_condition & (s3_data[key].astype(str) == str(expected_value))

                    # Only proceed if we have fields to filter on
                    if filter_fields:
                        matching_rows = s3_data[matching_condition]

                        if len(matching_rows) > 0:
                            active_rows = matching_rows[matching_rows[HUDI_DELETION_COLUMN] != "true"]

                            if len(active_rows) > 0:
                                changes_validated += 1
                                self.logging.info(f"✓ Insert validated - found {len(active_rows)} matching active record(s)")
                            else:
                                failed_validations.append(f"Insert found but all matching records are marked as deleted: {filter_fields}")
                        else:
                            failed_validations.append(f"Insert not found with matching fields: {filter_fields}")
                    else:
                        failed_validations.append(f"No valid fields to match for insert validation: {inserted_data}")

                elif change['operation'] == 'update':
                    # Check if the updated record reflects the changes
                    updated_data = change['data']
                    where_clause = f"{change['where_column']} = {change['where_value']}"

                    # Extract ID from where clause
                    pk_value = self._extract_pk_from_where_clause(where_clause, pk_col)

                    if pk_value:
                        pk_value_str = str(pk_value)
                        matching_rows = s3_data[s3_data[HUDI_RECORD_KEY].astype(str) == pk_value_str]

                        if len(matching_rows) > 0:
                            row = matching_rows.iloc[0]

                            # Check if it's not marked as deleted
                            if HUDI_DELETION_COLUMN in row and row[HUDI_DELETION_COLUMN] == "true":
                                failed_validations.append(f"Update target found but marked as deleted: ID {pk_value}")
                            else:
                                # Validate updated fields
                                field_mismatches = []
                                for key, expected_value in updated_data.items():
                                    if key in row.index:
                                        actual_value = row[key]
                                        # Convert for comparison
                                        if str(actual_value) != str(expected_value):
                                            field_mismatches.append(f"{key}: expected {expected_value}, got {actual_value}")
                                    else:
                                        field_mismatches.append(f"{key}: field not found in S3 data")

                                if field_mismatches:
                                    failed_validations.append(f"Update validation failed for ID {pk_value}: {field_mismatches}")
                                else:
                                    changes_validated += 1
                                    self.logging.info(f"✓ Update validated for ID: {pk_value}")
                        else:
                            failed_validations.append(f"Update target not found: {where_clause}")
                    else:
                        failed_validations.append(f"Could not extract primary key from where clause: {where_clause}")


                elif change['operation'] == 'delete':
                    # Check if the deleted record is marked as deleted in the datalake
                    where_clause = f"{change['where_column']} = {change['where_value']}"

                    # Extract ID from where clause
                    pk_value = self._extract_pk_from_where_clause(where_clause, pk_col)

                    if pk_value:
                        pk_value_str = str(pk_value)
                        matching_rows = s3_data[s3_data[HUDI_RECORD_KEY].astype(str) == pk_value_str]

                        if len(matching_rows) > 0:
                            row = matching_rows.iloc[0]

                            # Check if it's marked as deleted
                            if HUDI_DELETION_COLUMN in row and row[HUDI_DELETION_COLUMN] == "true":
                                changes_validated += 1
                                self.logging.info(f"✓ Delete validated for ID: {pk_value}")
                            else:
                                failed_validations.append(f"Delete target found but not marked as deleted: ID {pk_value}")
                        else:
                            failed_validations.append(f"Delete target not found. ID {pk_value}")
                    else:
                        failed_validations.append(f"Could not extract primary key from where clause: {where_clause}")

            if len(failed_validations) == 0:
                result = ValidationResult.PASS
                details = f"All {changes_validated} changes validated successfully"

            else:
                result = ValidationResult.FAIL
                details = f"Failed validations: {failed_validations}"

            return TestResult(
                test_name=f"change_propagation_validation_{table_name}",
                result=result,
                details=details,
                timestamp=datetime.now(),
                metrics={"validated_changes": changes_validated, "failed_changes": len(failed_validations)}
            )

        except Exception as e:
            self.logging.error('An error occured', e)
            return TestResult(
                test_name=f"change_propagation_validation_{table_name}",
                result=ValidationResult.FAIL,
                details=f"Error during change validation: {str(e)}",
                timestamp=datetime.now()
            )