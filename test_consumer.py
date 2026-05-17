from kafka import KafkaConsumer
import json
import os

# Connect to the Kafka topic
kafka_broker = os.environ.get('KAFKA_BROKER', 'localhost:9092')
consumer = KafkaConsumer(
    'v2x-telemetry',
    bootstrap_servers=[kafka_broker],
    auto_offset_reset='latest', # Start reading at the newest message
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

print("Listening to Kafka Firehose... (Press Ctrl+C to stop)")

for message in consumer:
    data = message.value
    print(f"RECEIVED via Kafka -> Vehicle: {data['vehicle_id']} | Speed: {data['velocity']:.2f}")