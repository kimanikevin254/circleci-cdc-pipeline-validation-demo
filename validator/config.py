"""Configuration settings"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "user": os.getenv("POSTGRES_USER", "cdc_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "cdc_password"),
    "database": os.getenv("POSTGRES_DATABASE", "cdc_db")
}

S3_CONFIG = {
    "bucket_name": os.getenv("S3_BUCKET_NAME", "cdc-bucket"),
    "access_key_id": os.getenv("S3_ACCESS_KEY_ID", "minioadmin"),
    "secret_access_key": os.getenv("S3_SECRET_ACCESS_KEY", "minioadmin"),
    "endpoint_url": os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
}

TABLE_CONFIGS = [
    {
        "table_name": "todos",
        "primary_key": "id"
    }
]

HUDI_RECORD_KEY = '_hoodie_record_key'
HUDI_DELETION_COLUMN = '__deleted'
PIPELINE_SYNC_WAIT_TIME_SECS = 20
S3_PATH_PREFIX = 'hudi-tables'