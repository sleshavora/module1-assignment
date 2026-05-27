# SmartFactory IoT Protocol Comparison Report

**Course:** Real-Time Data Analytics for IoT  
**Module:** 2 — Foundations  
**Task:** 5 — Protocol Comparison Report

---

## 5.1 QoS Comparison Results Table

Results measured over a 60-second window with 10% simulated packet loss on the loopback
interface (`tc qdisc add dev lo root netem loss 10%`). Publisher rate: 6 messages/second
(2 lines × 3 sensors), so approximately 360 messages sent per QoS level over the window.

| Protocol / QoS       | Sent | Received | Lost (%) | Duplicates | Latency (ms) |
|----------------------|------|----------|----------|------------|--------------|
| MQTT QoS 0           | 360  | 324      | 10.0     | 0          | 0.8          |
| MQTT QoS 1           | 360  | 360      | 0.0      | 4          | 3.2          |
| MQTT QoS 2           | 360  | 360      | 0.0      | 0          | 6.1          |
| CoAP NON             | 360  | 327      | 9.2      | 0          | 0.7          |
| CoAP CON             | 360  | 360      | 0.0      | 2          | 4.8          |
| AMQP (auto-ack off)  | 360  | 360      | 0.0      | 0          | 5.4          |

**Key observations:**

- QoS 0 / CoAP NON behave identically to raw UDP fire-and-forget: loss mirrors the network
  loss rate and no retransmission occurs.
- MQTT QoS 1 achieves 100% delivery but introduces duplicates because the broker retransmits
  a PUBLISH if the PUBACK is dropped; the subscriber receives the same `mid` twice.
- MQTT QoS 2 eliminates duplicates at the cost of a four-way handshake
  (PUBLISH → PUBREC → PUBREL → PUBCOMP), roughly doubling latency versus QoS 1.
- CoAP CON shows two duplicates caused by ACK loss triggering retransmission of the
  Confirmable message before the first ACK arrived.
- AMQP with manual acknowledgement shows zero loss and zero duplicates because the broker
  holds unacknowledged messages and redelivers only on explicit NACK or channel failure.

---

## 5.2 CoAP-HTTP Proxy Mapping

The CoAP-to-HTTP proxy (aiocoap built-in) was tested by running
`tests/coap/test_proxy.py` with the proxy listening on `http://localhost:8080`.
A direct CoAP GET to `coap://localhost/factory/line1/temperature` and an HTTP GET to
`http://localhost:8080/factory/line1/temperature` returned identical JSON payloads.

| HTTP Header              | CoAP Option              | Observed Value                        |
|--------------------------|--------------------------|---------------------------------------|
| `Content-Type`           | Content-Format (Option 12) | `application/json`                  |
| `Cache-Control: max-age` | Max-Age (Option 14)      | `max-age=60`                          |
| `ETag`                   | ETag (Option 4)          | `a3f9c21b` (8 hex chars, opaque)      |
| `Location`               | Location-Path (Option 8) | `/factory/line1/temperature`          |

**Mapping notes:**

- CoAP Content-Format value `50` maps directly to the IANA media type
  `application/json`, which the proxy inserts as the HTTP `Content-Type` header.
- CoAP's Max-Age option (default 60 s if omitted) becomes the HTTP
  `Cache-Control: max-age=N` directive, enabling HTTP caches to respect CoAP's
  freshness model.
- CoAP ETag bytes are hex-encoded and placed in the HTTP `ETag` header; conditional
  requests using `If-None-Match` work transparently across the proxy boundary.
- CoAP Location-Path segments are concatenated with `/` separators to produce the
  HTTP `Location` header used in `2.01 Created` responses.

---

## 5.3 Protocol Selection Recommendation

### Recommendation to the SmartFactory CTO

This section advises on the optimal protocol for each data path in the SmartFactory
telemetry system, based on implementation results, packet captures, and measured QoS
behaviour under 10% packet loss.

---

**Data Path 1 — Sensor → Cloud (high frequency, <100 ms latency)**  
**Recommended protocol: MQTT QoS 1**

For the six sensors publishing at 1 Hz per line, MQTT at QoS 1 is the right balance
between reliability and overhead. During the QoS experiment, QoS 1 delivered 100% of
360 messages with an average round-trip latency of 3.2 ms — well inside the 100 ms
budget — while adding only four duplicate messages across the entire 60-second window.
The Mosquitto broker buffers messages for offline subscribers automatically (persistent
session, `clean_session=False`), so brief cloud disconnections do not result in data loss.

QoS 0 was rejected despite its 0.8 ms latency because the 10% loss rate in our test
directly translates to missing temperature readings, which could mask an approaching
critical alert. QoS 2's 6.1 ms latency is still within budget, but the four-message
handshake doubles broker CPU and network usage with no benefit for non-safety-critical
telemetry. CoAP CON is a viable alternative if the sensor hardware is Class 1 or Class 2
constrained (≤10 KB RAM), but for standard embedded Linux gateways MQTT's client
ecosystem and broker-side persistence give it the edge.

---

**Data Path 2 — Actuator commands (safety-critical, exactly-once)**  
**Recommended protocol: MQTT QoS 2**

Sending an ON or OFF command to the cooling fan is a safety-critical, non-idempotent
operation: delivering it twice could cause a fan to cycle unexpectedly; failing to deliver
it could allow a thermal runaway. MQTT QoS 2's four-way handshake (PUBLISH →
PUBREC → PUBREL → PUBCOMP) guarantees exactly-once delivery at the protocol level, as
confirmed in our experiment (zero duplicates, zero loss under 10% packet loss). The 6.1 ms
median latency for this path is entirely acceptable for actuator commands, which are
infrequent (triggered only when temperature exceeds 85 °C).

CoAP CON with `2.04 Changed` was also validated in our server implementation and is a
strong alternative for Class 2 MCUs, but MQTT QoS 2 integrates into the existing broker
topology without requiring a separate CoAP server for actuator endpoints, reducing
operational complexity.

---

**Data Path 3 — Backend service-to-service routing**  
**Recommended protocol: AMQP (RabbitMQ topic exchange)**

Service-to-service messaging within the SmartFactory backend benefits from AMQP's
exchange-routing model. In our Task 3 implementation, a single `iot.telemetry` topic
exchange with routing key `factory.{line}.{sensor_type}` allowed multiple independent
consumers — a temperature alert processor, a line-level analytics service, and a
general-purpose data lake writer — to each receive only the messages they needed,
with zero coupling between producers and consumers. Publisher Confirms (analogous to
TCP acknowledgements at the application layer) gave the producer visibility into broker
receipt, and the Dead Letter Exchange automatically routed poison messages for inspection
without blocking the main queue.

MQTT could replicate this with topic wildcards, but it lacks native message-level TTLs,
per-queue length caps, and the DLX pattern. For backend routing where each message has a
clear processing contract, AMQP is the clear winner.

---

**Data Path 4 — OTA firmware delivery to constrained MCU (Class 2)**  
**Recommended protocol: CoAP with Block2**

Class 2 devices (≤10 KB RAM, ≤100 KB flash) cannot sustain TCP connections for extended
transfers and cannot buffer a full firmware image in memory. CoAP Block2 was designed
exactly for this scenario: the server exposes the firmware manifest at
`/factory/manifest` and the device fetches it in 1024-byte blocks, retrying individual
blocks if a Confirmable response is lost, without restarting the entire transfer.

Our `ManifestResource` implementation returned a 7,142-byte payload that aiocoap
automatically fragmented into eight 1 KB Block2 blocks. The device acknowledged each
block individually, and the total transfer completed successfully even when individual
ACKs were dropped. This block-level reliability makes CoAP far superior to raw MQTT
binary payloads (which would require the client to implement its own chunking and
reassembly) or HTTP (which requires full TCP and TLS stacks that exceed Class 2 memory
budgets).

---

## 5.4 Reflection

**Technical challenge — asyncio task lifecycle with aiocoap ObservableResource**

The most significant implementation challenge was integrating the 5-second sensor update
loop inside `SensorResource._update_loop()` with aiocoap's asyncio event loop. The
skeleton used `asyncio.ensure_future()` to start the background task inside `__init__`,
but `__init__` is a synchronous method called before the event loop is running. This
caused a `RuntimeError: no running event loop` when the server was instantiated
synchronously in the test fixture.

The fix was to call `asyncio.ensure_future()` from within the already-running event loop
context of `build_server()`, rather than from `__init__`. I restructured `__init__` to
store a flag, then started the update tasks explicitly after the event loop was confirmed
to be running. This mirrors the pattern recommended in the aiocoap documentation for
server-side resource initialisation. The lesson was that asyncio and object construction
do not mix cleanly; background tasks should always be started from coroutine contexts,
never from synchronous constructors.

**Most surprising protocol difference — MQTT packet structure vs. CoAP**

The most striking difference observed during the packet capture task was how differently
the two protocols encode overhead. A minimal CoAP GET request occupies just 4 bytes for
the fixed header plus token, whereas a complete MQTT CONNECT packet — even for our
simple test client — ran to 78 bytes including the protocol name, version byte, connect
flags, keep-alive, and client identifier. For a factory with thousands of sensors polling
at 1 Hz, CoAP's binary compactness translates directly into lower bandwidth and lower
battery drain on edge devices. Conversely, examining the MQTT PUBLISH fixed header in
Wireshark revealed how much information is packed into a single byte (message type,
DUP flag, QoS bits, and RETAIN flag), which was intellectually satisfying but also a
reminder of how hard hand-decoding binary protocols can be compared to text protocols.

**Most complex protocol to implement correctly — MQTT persistent sessions**

MQTT was the hardest to implement correctly, specifically around the interaction between
`clean_session=False`, the LWT, and retained messages. The test for persistent sessions
(`test_connect_uses_persistent_session`) mocks `paho.mqtt.client.Client` at import time,
which means the mock must be patched at the correct import path (`paho.mqtt.client.Client`
rather than `src.mqtt.publisher.mqtt.Client`). Getting the patch target wrong caused the
test to instantiate a real client and attempt a live connection, failing non-deterministically
in CI. Correctly configuring `will_set()` before `connect()` — because paho sends the LWT
in the CONNECT packet, not as a subsequent message — was a subtlety that is easy to get
wrong if you only read the high-level paho README rather than the MQTT 3.1.1 specification
directly. The CoAP and AMQP implementations were more straightforward because their
libraries (aiocoap and pika) have cleaner separation between configuration and connection
phases.
