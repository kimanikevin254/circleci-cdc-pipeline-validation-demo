"""Data access layer for PostgreSQL and S3 operations"""

import logging
from typing import Dict, Any, List
from io import BytesIO

import boto3
import psycopg2
import pandas as pd
from psycopg2.extras import RealDictCursor

from config import S3_PATH_PREFIX


class DataAccessManager:
    def __init__(self, postgres_config: Dict[str, Any], s3_config: Dict[str, Any],):
        self.postgres_config = postgres_config
        self.s3_config = s3_config
        self.logging = logging.getLogger(__name__)

        self.pg_conn = None
        self.s3_client = None
        self._initialize_connections()

    def _initialize_connections(self):
        """Initialize PostgreSQL and S3 connections"""
        try:
            # PostgreSQL connection
            self.pg_conn = psycopg2.connect(**self.postgres_config)
            self.logging.info("PostgreSQL connection established.")

            # S3 connection
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.s3_config['access_key_id'],
                aws_secret_access_key=self.s3_config['secret_access_key'],
                endpoint_url=self.s3_config["endpoint_url"]
            )
            self.logging.info("S3 connection established.")

        except Exception as e:
            self.logging.error(f"Error establishing connections: {e}")
            raise

    def get_postgres_data(self, table_name: str, where_clause: str = None) -> pd.DataFrame:
        """Fetch data from PostgreSQL table"""
        query = f"SELECT * FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"

        with self.pg_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query)
            data = cursor.fetchall()
            return pd.DataFrame(data)
        
    def get_s3_data(self, s3_path: str = None) -> pd.DataFrame:
        """Fetch data from S3 (latest parquet file)"""
        s3_path = f"{S3_PATH_PREFIX}/{s3_path}"

        # List all parquest files in the S3 path
        bucket = self.s3_config['bucket_name']
        response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=s3_path)

        if 'Contents' not in response:
            self.logging.warning(f"No files found in S3 path: {s3_path}")
            return pd.DataFrame()
        
        # Filter for Parquet files only
        parquet_files = [
            obj for obj in response.get('Contents', [])
            if obj['Key'].endswith('.parquet')
        ]

        if not parquet_files:
            self.logging.info(f"No parquet files found in S3 path: {s3_path}")
            return pd.DataFrame()
        
        # Get the latest file by LastModified timestamp
        latest_file = max(parquet_files, key=lambda x: x['LastModified'])

        # Read the latest parquet file
        content = self.s3_client.get_object(Bucket=bucket, Key=latest_file['Key'])
        body = BytesIO(content['Body'].read())
        df = pd.read_parquet(body)

        return df
    
    def close_pg_connection(self):
        """Close the PostgreSQL database connection"""
        if self.pg_conn:
            self.pg_conn.close()
            self.logging.info('PostgreSQL connection closed.')

    def execute_changes(self, table_name: str, changes: List[Dict[str, Any]]):
        """
        Make controlled changes to the PostgreSQL database.

        Args:
            table_name (str): The name of the table to modify.
            changes (List[Dict[str, Any]]): A list of dictionaries representing the changes to apply.
                [
                    {"operation": "insert", "data": {...}},
                    {"operation": "update", "data": {...}, "where_column": "id", "where_value": 1},
                    {"operation": "delete", "where_column": "id", "where_value": 2}
                ]
        """

        with self.pg_conn.cursor() as cursor:
            for change in changes:
                sql = None
                params = []
                try:
                    operation = change['operation']

                    if operation == 'insert':
                        columns = list(change['data'].keys())
                        values_placeholders = ', '.join(['%s'] * len(columns))
                        sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({values_placeholders})"
                        params = list(change['data'].values())

                    elif operation == 'update':
                        set_clauses = []
                        for k, v in change['data'].items():
                            set_clauses.append(f"{k} = %s")
                            params.append(v)
                        set_clause_str = ', '.join(set_clauses)

                        where_column = change['where_column']
                        where_value = change['where_value']
                        sql = f"UPDATE {table_name} SET {set_clause_str} WHERE {where_column} = %s"
                        params.append(where_value)

                    elif operation == 'delete':
                        where_column = change['where_column']
                        where_value = change['where_value']
                        sql = f"DELETE FROM {table_name} WHERE {where_column} = %s"
                        params.append(where_value)
                    else:
                        self.logging.warning(f"Unsupported operation: {operation}. Skipping change.")
                        continue

                    if sql:
                        cursor.execute(sql, params)
                        self.logging.info(f"Executed SQL (template): {sql} with parameters: {params}")

                except Exception as e:
                    self.logging.error(f"Error executing change for operation '{operation}': {e}")
                    self.pg_conn.rollback()
                    raise

            self.pg_conn.commit()
            return