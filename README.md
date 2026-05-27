# Module 1 Assignment — SmartFactory IoT Protocol Integration

**Course:** Real-Time Data Analytics for IoT
**Module:** 2 — Foundations

---

## Test Results

22 passed, 8 skipped (AMQP — excluded per instructions)

---

## Quick Start

\`\`\`bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start Docker services (Mosquitto broker)
docker compose up -d

# 3. Run all tests
pytest tests/ -v --tb=short
\`\`\`

---

## Running Components Manually

Open separate terminals for each:

\`\`\`bash
# Terminal 1 — CoAP Server
python -m src.coap.server

# Terminal 2 — MQTT Publisher
python -m src.mqtt.publisher

# Terminal 3 — MQTT Subscriber
python -m src.mqtt.subscriber

# Terminal 4 — CoAP Observer (runs for 60s then exits)
python -m src.coap.observer
\`\`\`

---

## Completed Tasks

| Task | Description | File | Status |
|------|-------------|------|--------|
| 1.1 | MQTT Publisher | src/mqtt/publisher.py | Complete |
| 1.2 | MQTT Subscriber | src/mqtt/subscriber.py | Complete |
| 2.1 | CoAP Server | src/coap/server.py | Complete |
| 2.2 | CoAP Observer | src/coap/observer.py | Complete |
| 4 | Packet Analysis | report/packet_analysis.md | Complete |
| 5 | Protocol Report | report/comparison_report.md | Complete |

Note: AMQP (Task 3) excluded per assignment instructions.

---

## Infrastructure

| Service | Port | Notes |
|---------|------|-------|
| Mosquitto MQTT | 1883 | Required for MQTT tasks |
| CoAP Server | 5683 | Python-based, no Docker needed |
| RabbitMQ | 5672 | Not used (AMQP skipped) |
