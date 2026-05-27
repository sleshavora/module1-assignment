"""
Module 1 Assignment — Task 2.2
CoAP Observer Client
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

import aiocoap
from aiocoap import Message, Code
from aiocoap.numbers.optionnumbers import OptionNumber

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
log = logging.getLogger(__name__)

SERVER_BASE      = "coap://localhost"
OBSERVE_DURATION = 60   # seconds


class FactoryObserver:
    """Observes CoAP sensor resources and reassembles Block2 transfers."""

    def __init__(self):
        self._ctx = None
        self._last_seq: dict[str, int] = {}
        self._stale_count: dict[str, int] = {}

    async def start(self) -> None:
        self._ctx = await aiocoap.Context.create_client_context()

    async def stop(self) -> None:
        if self._ctx:
            await self._ctx.shutdown()

    async def observe_resource(self, uri: str) -> None:
        request = Message(code=Code.GET, uri=uri, observe=0)
        pr      = self._ctx.request(request)

        try:
            async def _watch():
                async for response in pr.observation:
                    self._handle_notification(uri, response)

            await asyncio.wait_for(_watch(), timeout=OBSERVE_DURATION)
        except asyncio.TimeoutError:
            pass
        finally:
            pr.observation.cancel()
            log.info("Deregistered from %s", uri)

    def _handle_notification(self, uri: str, response: Message) -> None:
        seq = response.opt.observe
        if seq is None:
            seq = 0

        last = self._last_seq.get(uri)
        if last is not None:
            # Handle wrap-around at 2^24
            wrapped = (seq - last) % (2 ** 24)
            if wrapped == 0 or wrapped > (2 ** 23):
                self._stale_count[uri] = self._stale_count.get(uri, 0) + 1
                log.warning("STALE notification on %s: seq=%d <= last=%d", uri, seq, last)
                return

        self._last_seq[uri] = seq

        try:
            data  = json.loads(response.payload.decode())
            value = data.get("value", "?")
            unit  = data.get("unit", "")
            ts    = data.get("ts", datetime.now(timezone.utc).isoformat())
        except (json.JSONDecodeError, UnicodeDecodeError):
            value, unit, ts = response.payload, "", ""

        print(f"[OBSERVE] {uri}  seq={seq}  val={value} {unit}  @ {ts}")

    async def fetch_manifest(self) -> None:
        uri     = f"{SERVER_BASE}/factory/manifest"
        request = Message(code=Code.GET, uri=uri)
        response = await self._ctx.request(request).response

        payload    = response.payload
        byte_count = len(payload)
        log.info("Manifest received: %d bytes", byte_count)

        try:
            data  = json.loads(payload.decode())
            count = len(data) if isinstance(data, list) else (
                len(data.get("firmware_entries", data)) if isinstance(data, dict) else 0
            )
            log.info("Firmware entries in manifest: %d", count)
        except (json.JSONDecodeError, UnicodeDecodeError):
            log.warning("Could not parse manifest as JSON")

        # Check block2 option if present
        if hasattr(response.opt, "block2") and response.opt.block2 is not None:
            blk = response.opt.block2
            log.info("Block2 transfer: block_number=%d, size_exponent=%d",
                     blk.block_number, blk.size_exponent)

        log.info("Block2 transfer complete")

    async def run(self) -> None:
        await self.start()
        try:
            uri1 = f"{SERVER_BASE}/factory/line1/temperature"
            uri2 = f"{SERVER_BASE}/factory/line2/temperature"

            log.info("Starting observation on %s and %s for %ds", uri1, uri2, OBSERVE_DURATION)
            await asyncio.gather(
                self.observe_resource(uri1),
                self.observe_resource(uri2),
            )

            log.info("Observations complete. Fetching manifest…")
            await self.fetch_manifest()

            print("\n── Stale Notification Summary ───────────────")
            for uri in (uri1, uri2):
                count = self._stale_count.get(uri, 0)
                print(f"  {uri}: {count} stale notification(s)")
            print("─────────────────────────────────────────────")
        finally:
            await self.stop()


if __name__ == "__main__":
    observer = FactoryObserver()
    asyncio.run(observer.run())
