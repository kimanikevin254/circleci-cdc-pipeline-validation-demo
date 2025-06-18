"""Test data generation utilities."""

import random
import pandas as pd
from faker import Faker
from typing import Dict, Any, Optional

class TestDataGenerator:
    def __init__(self):
        self.fake = Faker()
        self._reserved_ids = set()
    
    def generate_test_data(self, table_name: str, purpose: str, existing_data: pd.DataFrame = None, primary_key: str = "id") -> Optional[Dict[str, Any]]:
        """Generate test data for insert, update and delete operations."""
        if table_name == 'todos':
            if purpose == 'insert':
                return {
                    "operation": "insert",
                    "data": {
                        "title": self.fake.sentence(nb_words=4),
                        "description": self.fake.paragraph(nb_sentences=2),
                        "completed": self.fake.boolean()
                    }
                }
            elif purpose == 'update':
                if existing_data.empty:
                    return None
                
                # Filter out reserved IDs
                available_data = existing_data[~existing_data[primary_key].isin(self._reserved_ids)]
                if available_data.empty:
                    self._reserved_ids.clear()  # Reset if no rows available
                    return None
                
                # Select a row to update
                random_row = available_data.sample(1).iloc[0]
                pk_value = int(random_row[primary_key])
                self._reserved_ids.add(pk_value)
                
                # Randomly choose fields to update
                update_data = {}
                if random.choice([True, False]):
                    update_data["title"] = self.fake.sentence(nb_words=3)
                if random.choice([True, False]):
                    update_data["description"] = self.fake.paragraph(nb_sentences=1)
                if random.choice([True, False]):
                    update_data["completed"] = not random_row.get("completed", False) # Toggle boolean
                
                if not update_data: # Ensure at least one field is updated
                    update_data["title"] = self.fake.sentence(nb_words=3) # Fallback to updating title
                
                return {
                    "operation": "update",
                    "data": update_data,
                    "where_column": primary_key,
                    "where_value": pk_value
                }
            elif purpose == 'delete':
                if existing_data.empty:
                    return None
                
                # Filter out reserved IDs
                available_data = existing_data[~existing_data[primary_key].isin(self._reserved_ids)]
                if available_data.empty:
                    self._reserved_ids.clear()  # Reset if no rows available
                    return None
                
                # Select a random row to delete
                random_row = available_data.sample(1).iloc[0]
                pk_value = int(random_row[primary_key])
                self._reserved_ids.add(pk_value)
                
                return {
                    "operation": "delete",
                    "where_column": primary_key,
                    "where_value": pk_value
                }
        return None