"""
Module 1 Assignment — Task 2.1
CoAP Sensor Resource Server
"""

import asyncio
import json
import logging
import random
from datetime import datetime, timezone

import aiocoap
import aiocoap.resource as resource
from aiocoap import Code, Message
from aiocoap.numbers.contentformat import ContentFormat

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
log = logging.getLogger(__name__)

SENSOR_CONFIG = {
    "temperature": {"unit": "C",    "base": 70.0, "noise": 3.0},
    "vibration":   {"unit": "mm/s", "base": 1.2,  "noise": 0.3},
    "power":       {"unit": "kW",   "base": 45.0, "noise": 5.0},
}

def _sim(sensor: str) -> dict:
    cfg = SENSOR_CONFIG[sensor]
    return {
        "value": round(cfg["base"] + random.gauss(0, cfg["noise"]), 3),
        "unit":  cfg["unit"],
        "ts":    datetime.now(timezone.utc).isoformat(),
    }

def _json(data: dict) -> bytes:
    return json.dumps(data).encode()


class SensorResource(resource.ObservableResource):

    def __init__(self, line: str, sensor_type: str):
        super().__init__()
        self.line        = line
        self.sensor_type = sensor_type
        self._reading    = _sim(sensor_type)
        self._task       = None

    def start(self):
        self._task = asyncio.ensure_future(self._update_loop())

    async def _update_loop(self) -> None:
        while True:
            await asyncio.sleep(5)
            self._reading = _sim(self.sensor_type)
            self.updated_state()

    async def render_get(self, request: Message) -> Message:
        return Message(
            code=Code.CONTENT,
            payload=_json(self._reading),
            content_format=ContentFormat.JSON,
        )


class ActuatorResource(resource.Resource):

    def __init__(self):
        super().__init__()
        self._state = "OFF"

    async def render_get(self, request: Message) -> Message:
        return Message(
            code=Code.CONTENT,
            payload=_json({"state": self._state}),
            content_format=ContentFormat.JSON,
        )

    async def render_put(self, request: Message) -> Message:
        try:
            data  = json.loads(request.payload.decode())
            state = data.get("state", "").upper()
            if state not in ("ON", "OFF"):
                raise ValueError(f"Invalid state: {state!r}")
        except (json.JSONDecodeError, ValueError, AttributeError) as exc:
            return Message(code=Code.BAD_REQUEST, payload=str(exc).encode())
        self._state = state
        log.info("Fan actuator → %s", self._state)
        return Message(code=Code.CHANGED, payload=_json({"state": self._state}))


class ManifestResource(resource.Resource):

    def __init__(self):
        super().__init__()
        self._payload = self._build_manifest()

    def _build_manifest(self) -> bytes:
        sensors = list(SENSOR_CONFIG.keys())
        lines   = ["line1", "line2"]
        entries = []
        for i in range(1, 51):
            line   = lines[i % len(lines)]
            sensor = sensors[i % len(sensors)]
            entries.append({
                "id": f"fw-{i:04d}",
                "device": f"smartfactory-{line}-{sensor}-sensor-{i:04d}",
                "line": line,
                "sensor_type": sensor,
                "firmware_version": f"{(i % 5) + 1}.{(i % 10)}.{i % 3}",
                "build_date": f"2025-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                "sha256": f"{'a' * 8}{i:08x}{'b' * 8}{i:08x}{'c' * 8}",
                "size_bytes": 1024 + i * 512,
                "update_url": f"coap://ota.smartfactory.internal/firmware/{line}/{sensor}/v{(i%5)+1}.{i%10}.{i%3}.bin",
                "changelog": f"Release {i}: Fixed sensor drift for {sensor} on {line}. Improved filtering. Reduced memory by {i%20+5}%.",
                "required": i % 3 == 0,
                "rollback_version": f"{max(1,(i%5))}.{i%10}.0",
            })
        manifest = {
            "schema_version": "2.1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "factory_id": "smartfactory-brisbane-001",
            "total_devices": len(entries),
            "firmware_entries": entries,
        }
        payload = json.dumps(manifest, indent=2).encode()
        log.info("Manifest size: %d bytes", len(payload))
        return payload

    async def render_get(self, request: Message) -> Message:
        return Message(
            code=Code.CONTENT,
            payload=self._payload,
            content_format=ContentFormat.JSON,
        )


async def build_server() -> aiocoap.Context:
    sensors = [
        (["factory", "line1", "temperature"], SensorResource("line1", "temperature")),
        (["factory", "line1", "vibration"],   SensorResource("line1", "vibration")),
        (["factory", "line1", "power"],       SensorResource("line1", "power")),
        (["factory", "line2", "temperature"], SensorResource("line2", "temperature")),
    ]
    root = resource.Site()
    for path, res in sensors:
        root.add_resource(path, res)
    root.add_resource(["actuator", "line1", "fan"], ActuatorResource())
    root.add_resource(["factory", "manifest"],      ManifestResource())
    root.add_resource([".well-known", "core"],
                      resource.WKCResource(root.get_resources_as_linkheader))
    context = await aiocoap.Context.create_server_context(root)
    for _, res in sensors:
        res.start()
    return context


async def main() -> None:
    context = await build_server()
    log.info("CoAP server running on coap://localhost:5683")
    await asyncio.get_event_loop().create_future()


if __name__ == "__main__":
    asyncio.run(main())
