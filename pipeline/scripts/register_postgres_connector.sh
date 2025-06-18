# Bash script to register a PostgreSQL connector with the CDC source

#!/bin/bash

# Register the PostgreSQL connector
curl -X POST "http://localhost:8083/connectors" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "postgres-connector",
    "config": {
      "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
      "database.hostname": "cdc-postgres",
      "database.port": "5432",
      "database.user": "debezium_user",
      "database.password": "debezium_password",
      "database.dbname": "cdc_db",
      "topic.prefix": "postgres",
      "plugin.name": "pgoutput",
      "table.include.list": "public.todos",
      "publication.name": "debezium_pub",
      "key.converter": "io.confluent.connect.avro.AvroConverter",
      "key.converter.schema.registry.url": "http://schema-registry:8081",
      "value.converter": "io.confluent.connect.avro.AvroConverter",
      "value.converter.schema.registry.url": "http://schema-registry:8081",
      "transforms": "unwrap",
      "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
      "transforms.unwrap.drop.tombstones": false,
      "transforms.unwrap.delete.handling.mode": "rewrite"
    }
  }'