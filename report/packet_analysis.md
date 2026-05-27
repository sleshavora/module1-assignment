# Packet Analysis — Task 4

**Course:** Real-Time Data Analytics for IoT  
**Module:** 2 — Foundations

Captures produced with:
```bash
bash scripts/capture.sh   # 30-second window
# Output: captures/mqtt.pcap, captures/coap.pcap
```

---

## 4.2 MQTT Packet Annotations

### Packet 1 — CONNECT

| Field                  | Hex Bytes        | Decoded Value                        |
|------------------------|------------------|--------------------------------------|
| Frame type byte        | `0x10`           | Fixed header: type=1 (CONNECT), flags=0 |
| Remaining length       | `0x4C`           | 76 bytes                             |
| Protocol name length   | `0x00 0x04`      | 4 bytes                              |
| Protocol name          | `4D 51 54 54`    | "MQTT"                               |
| Protocol version byte  | `0x04`           | Version 3.1.1                        |
| Connect flags byte     | `0xC2`           | `1100 0010` — Username=1, Password=1, WillRetain=0, WillQoS=0, WillFlag=0, CleanSession=1, Reserved=0 |
| Keep-alive             | `0x00 0x3C`      | 60 seconds                           |
| Client ID              | `73 6D 61 72 74…`| "smartfactory-publisher-001"         |

**Connect flags byte expansion (`0xC2` = `1100 0010`):**

| Bit 7 | Bit 6 | Bit 5 | Bit 4 | Bit 3 | Bit 2 | Bit 1 | Bit 0 |
|-------|-------|-------|-------|-------|-------|-------|-------|
| Username=1 | Password=1 | WillRetain=0 | WillQoS[1]=0 | WillQoS[0]=0 | WillFlag=0 | CleanSession=1 | Reserved=0 |

---

### Packet 2 — QoS 1 PUBLISH (temperature reading)

| Field               | Hex Bytes           | Decoded Value                                      |
|---------------------|---------------------|----------------------------------------------------|
| Fixed header byte   | `0x32`              | `0011 0010` — type=3 (PUBLISH), DUP=0, QoS=01, RETAIN=0 |
| Remaining length    | `0x5E`              | 94 bytes                                           |
| Topic length field  | `0x00 0x1B`         | 27 bytes                                           |
| Topic string bytes  | `66 61 63 74 6F 72 79 2F 6C 69 6E 65 31 2F 74 65 6D 70 65 72 61 74 75 72 65` | "factory/line1/temperature" |
| Packet Identifier   | `0x00 0x01`         | 1                                                  |
| Payload             | `7B 22 6C 69 6E 65…`| `{"line":"line1","sensor":"temperature","value":72.441,...}` |

**Fixed header byte expansion (`0x32` = `0011 0010`):**

| Bit 7 | Bit 6 | Bit 5 | Bit 4 | Bit 3 | Bit 2 | Bit 1 | Bit 0 |
|-------|-------|-------|-------|-------|-------|-------|-------|
| Type[3]=0 | Type[2]=0 | Type[1]=1 | Type[0]=1 | DUP=0 | QoS[1]=0 | QoS[0]=1 | RETAIN=0 |

---

### Packet 3 — PUBACK

| Field             | Hex Bytes   | Decoded Value        |
|-------------------|-------------|----------------------|
| Fixed header byte | `0x40`      | type=4 (PUBACK), flags=0 |
| Remaining length  | `0x02`      | 2 bytes              |
| Packet Identifier | `0x00 0x01` | **1** ✓ (matches PUBLISH) |

The Packet Identifier `0x00 0x01` in the PUBACK matches the PUBLISH above, confirming
the broker acknowledged exactly that message.

---

## 4.3 CoAP Packet Annotations

### Packet 4 — CON GET Request (`/factory/line1/temperature`)

| Field               | Hex Bytes       | Decoded Value                                         |
|---------------------|-----------------|-------------------------------------------------------|
| Byte 0 (header)     | `0x44`          | `0100 0100` — Ver=01, Type=00 (CON), TKL=0100 (4)    |
| Byte 1 (Code)       | `0x01`          | 0.01 = GET                                            |
| Bytes 2–3 (Msg ID)  | `0xCA 0xFE`     | Message ID = 51966                                    |
| Token (4 bytes)     | `A1 B2 C3 D4`   | Token = 0xA1B2C3D4                                    |
| Option: Uri-Path 1  | `0xB7 66 61 63…`| Delta=11 (Uri-Path), Len=7, Value="factory"           |
| Option: Uri-Path 2  | `0x05 6C 69 6E…`| Delta=0, Len=5, Value="line1"                         |
| Option: Uri-Path 3  | `0x0B 74 65 6D…`| Delta=0, Len=11, Value="temperature"                  |

**Byte 0 expansion (`0x44` = `0100 0100`):**

| Bits 7–6 (Ver) | Bits 5–4 (Type) | Bits 3–0 (TKL) |
|----------------|-----------------|-----------------|
| 01 = Version 1 | 00 = CON        | 0100 = 4 bytes  |

**Uri-Path delta encoding** — the first Uri-Path option has delta=11 (Option Number 11).
Each subsequent Uri-Path uses delta=0 (same option number repeated), which is the
standard CoAP technique for multi-segment paths.

---

### Packet 5 — ACK 2.05 Content Response

| Field                   | Hex Bytes        | Decoded Value                               |
|-------------------------|------------------|---------------------------------------------|
| Byte 0 (header)         | `0x64`           | `0110 0100` — Ver=01, Type=10 (ACK), TKL=4  |
| Byte 1 (Code)           | `0x45`           | 2.05 = Content                              |
| Bytes 2–3 (Msg ID)      | `0xCA 0xFE`      | Message ID = 51966 ✓ (matches CON request)  |
| Token (4 bytes)         | `A1 B2 C3 D4`    | **Matches request token** ✓                 |
| Content-Format option   | `0xC1 0x32`      | Option 12 (Content-Format), value=50 (JSON) |
| Payload marker          | `0xFF`           | 0xFF — separates options from payload       |
| Payload                 | `7B 22 76 61 6C…`| `{"value":71.823,"unit":"C","ts":"2025-…"}` |

The Token `A1 B2 C3 D4` in the ACK response matches the Token in the CON GET request,
confirming the client can correlate this response with its outstanding request.

---

### Packet 6 — Observe Notification

| Field           | Value             | Notes                                         |
|-----------------|-------------------|-----------------------------------------------|
| Observe option  | Option Number 6   | Observe option present → this is a notification |
| Sequence value  | `0x000003`        | 3 (increments with each notification)         |
| Code            | 2.05 Content      | Normal content response                       |

The Observe option value acts as a freshness indicator: the client compares the incoming
sequence number against the last-seen value and discards the notification if the
sequence number is lower (accounting for wrap-around at 2²⁴ per RFC 7641 §3.4).

---

## Notes on AMQP Capture

Per the assignment instructions, AMQP (Task 4.4) is skipped this submission.
The `captures/amqp.pcap` file is present but unannotated.
