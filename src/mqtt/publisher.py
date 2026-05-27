"""
Module 1 Assignment — Task 1.1
MQTT Sensor Publisher
"""

import json
import logging
import random
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional

import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

BROKER_HOST = "localhost"
BROKER_PORT = 1883
CLIENT_ID   = "smartfactory-publisher-001"

LINES   = ["line1", "line2"]
SENSORS = {
    "temperature": {"unit": "C",    "base": 70.0, "noise": 3.0,  "qos": 1},
    "vibration":   {"unit": "mm/s", "base": 1.2,  "noise": 0.3,  "qos": 0},
    "power":       {"unit": "kW",   "base": 45.0, "noise": 5.0,  "qos": 2},
}

CRITICAL_TEMP_THRESHOLD = 85.0


@dataclass
class SensorReading:
    line:      str
    sensor:    str
    value:     float
    unit:      str
    timestamp: str
    seq:       int


class SmartFactoryPublisher:
    """Publishes simulated sensor data for the SmartFactory assignment."""

    def __init__(self, broker_host: str = BROKER_HOST, broker_port: int = BROKER_PORT):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self._seq: dict[str, int] = {}
        self._client: Optional[mqtt.Client] = None
        self._connected = False

    def _build_client(self) -> mqtt.Client:
        client = mqtt.Client(client_id=CLIENT_ID, clean_session=False)
        client.on_connect = self.on_connect
        client.on_publish = self.on_publish
        # LWT for line1 (paho supports one LWT per client)
        client.will_set(
            topic="factory/line1/status",
            payload="offline",
            qos=1,
            retain=True,
        )
        self._client = client
        return client

    def connect(self) -> None:
        client = self._build_client()
        client.connect(self.broker_host, self.broker_port)
        client.loop_start()
        # Wait up to 5 seconds for connection
        deadline = time.time() + 5
        while not self._connected and time.time() < deadline:
            time.sleep(0.1)
        # Publish retained 'online' for each line
        for line in LINES:
            client.publish(f"factory/{line}/status", "online", qos=1, retain=True)
            log.info("Published 'online' status for %s", line)

    def disconnect(self) -> None:
        if self._client is None:
            return
        for line in LINES:
            self._client.publish(f"factory/{line}/status", "offline", qos=1, retain=True)
        self._client.loop_stop()
        self._client.disconnect()
        log.info("Disconnected cleanly")

    def on_connect(self, client, userdata, flags, rc: int) -> None:
        if rc == 0:
            log.info("Connected (rc=%d)", rc)
            self._connected = True
        else:
            log.error("Connection refused: %d", rc)

    def on_publish(self, client, userdata, mid: int) -> None:
        log.debug("PUBACK received for mid=%d", mid)

    def _simulate_reading(self, line: str, sensor: str) -> SensorReading:
        cfg   = SENSORS[sensor]
        value = round(cfg["base"] + random.gauss(0, cfg["noise"]), 3)
        key   = f"{line}/{sensor}"
        self._seq[key] = self._seq.get(key, 0) + 1
        return SensorReading(
            line=line,
            sensor=sensor,
            value=value,
            unit=cfg["unit"],
            timestamp=datetime.now(timezone.utc).isoformat(),
            seq=self._seq[key],
        )

    def _topic(self, line: str, sensor: str) -> str:
        return f"factory/{line}/{sensor}"

    def publish_reading(self, line: str, sensor: str) -> SensorReading:
        reading = self._simulate_reading(line, sensor)
        topic   = self._topic(line, sensor)
        qos     = SENSORS[sensor]["qos"]
        payload = json.dumps(asdict(reading))
        self._client.publish(topic, payload, qos=qos)
        log.info(
            "[%s/%s] value=%s %s  QoS=%d  seq=%d",
            line, sensor, reading.value, reading.unit, qos, reading.seq,
        )
        return reading

    def run(self, interval_s: float = 1.0) -> None:
        self.connect()
        log.info("Publishing started (Ctrl-C to stop)")
        try:
            while True:
                for line in LINES:
                    for sensor in SENSORS:
                        self.publish_reading(line, sensor)
                time.sleep(interval_s)
        except KeyboardInterrupt:
            log.info("Shutting down…")
        finally:
            self.disconnect()


if __name__ == "__main__":
    pub = SmartFactoryPublisher()
    pub.run()
