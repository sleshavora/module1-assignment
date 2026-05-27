# Module 1 Assignment — SmartFactory IoT Protocol Integration

**Real-Time Data Analytics for IoT** · Graduate Course · Module 2

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start Docker services (Mosquitto broker)
docker compose up -d

# 3. Run MQTT components (two terminals)
python -m src.mqtt.publisher       # Terminal 1
python -m src.mqtt.subscriber      # Terminal 2

# 4. Run CoAP components (two terminals)
python -m src.coap.server          # Terminal 1
python -m src.coap.observer        # Terminal 2

# 5. Run all tests
pytest tests/ -v --tb=short
```

---

## Completed Tasks

| Task | File | Status |
|------|------|--------|
| 1.1 MQTT Publisher | `src/mqtt/publisher.py` | ✅ Complete |
| 1.2 MQTT Subscriber | `src/mqtt/subscriber.py` | ✅ Complete |
| 2.1 CoAP Server | `src/coap/server.py` | ✅ Complete |
| 2.2 CoAP Observer | `src/coap/observer.py` | ✅ Complete |
| 4 Packet Analysis | `report/packet_analysis.md` | ✅ Complete |
| 5 Protocol Report | `report/comparison_report.md` | ✅ Complete |

Note: AMQP (Task 3) is omitted per assignment instructions.

---

## Infrastructure

| Service | Port |
|---------|------|
| Mosquitto MQTT | 1883 |
| CoAP server (Python) | 5683 |

```bash
docker compose up -d      # Start Mosquitto
docker compose down       # Stop all services
```
