from dataclasses import dataclass
from json import dumps
from os import getenv
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class KafkaConfig:
    enabled: bool
    bootstrap_servers: str
    input_topic: str
    output_topic: str
    client_id: str


def load_kafka_config() -> KafkaConfig:
    return KafkaConfig(
        enabled=getenv("KAFKA_ENABLED", "false").lower() == "true",
        bootstrap_servers=getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        input_topic=getenv("KAFKA_INPUT_TOPIC", "p1.machine.risk.assessed"),
        output_topic=getenv("KAFKA_OUTPUT_TOPIC", "p2.self.healing.results"),
        client_id=getenv("KAFKA_CLIENT_ID", "p2-self-healing"),
    )


def _build_producer(config: KafkaConfig):
    from kafka import KafkaProducer

    return KafkaProducer(
        bootstrap_servers=config.bootstrap_servers,
        client_id=config.client_id,
        value_serializer=lambda value: dumps(value).encode("utf-8"),
        key_serializer=lambda value: value.encode("utf-8") if isinstance(value, str) else value,
        retries=3,
        linger_ms=10,
    )


def publish_event(event: Dict[str, Any], topic: Optional[str] = None, key: Optional[str] = None):
    config = load_kafka_config()
    if not config.enabled:
        return {"published": False, "reason": "kafka_disabled"}

    producer = _build_producer(config)
    topic_name = topic or config.input_topic
    record_key = key or event.get("correlation_id") or event.get("event_id")
    future = producer.send(topic_name, key=record_key, value=event)
    metadata = future.get(timeout=10)
    producer.flush()
    producer.close()
    return {
        "published": True,
        "topic": metadata.topic,
        "partition": metadata.partition,
        "offset": metadata.offset,
    }


def create_consumer():
    from kafka import KafkaConsumer

    config = load_kafka_config()
    return KafkaConsumer(
        config.input_topic,
        bootstrap_servers=config.bootstrap_servers,
        client_id=config.client_id,
        group_id=f"{config.client_id}-group",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda value: __import__("json").loads(value.decode("utf-8")),
        key_deserializer=lambda value: value.decode("utf-8") if value else None,
    )
