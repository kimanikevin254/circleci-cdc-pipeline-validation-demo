#!/bin/bash

docker exec spark bash -c "
    spark-submit \
    --jars $(echo $SPARK_HOME/jars/*.jar | tr ' ' ',') \
    --class org.apache.hudi.utilities.streamer.HoodieStreamer /opt/bitnami/spark/jars/hudi-utilities-slim-bundle_2.12-1.0.1.jar \
    --table-type COPY_ON_WRITE \
    --target-base-path s3a://cdc-bucket/hudi-tables/todos \
    --target-table todos \
    --source-class org.apache.hudi.utilities.sources.AvroKafkaSource \
    --source-ordering-field id \
    --payload-class org.apache.hudi.common.model.OverwriteWithLatestAvroPayload \
    --schemaprovider-class org.apache.hudi.utilities.schema.SchemaRegistryProvider \
    --min-sync-interval-seconds 10 \
    --op UPSERT \
    --continuous \
    --hoodie-conf bootstrap.servers=kafka:29092 \
    --hoodie-conf schema.registry.url=http://schema-registry:8081 \
    --hoodie-conf hoodie.streamer.schemaprovider.registry.url=http://schema-registry:8081/subjects/postgres.public.todos-value/versions/latest \
    --hoodie-conf hoodie.streamer.source.kafka.topic=postgres.public.todos \
    --hoodie-conf auto.offset.reset=earliest \
    --hoodie-conf hoodie.datasource.write.recordkey.field=id \
    --hoodie-conf hoodie.datasource.write.schema.allow.auto.evolution=true
"
