from collections.abc import Awaitable, Coroutine
import logging
import json
import os

from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
import websockets, websockets.client


UMBREON_HOST = os.environ['UMBREON_HOST']
UMBREON_PLATFORM_INSTANCE = os.environ['UMBREON_PLATFORM_INSTANCE']
UMBREON_USER_ENVIRONMENT = os.environ['UMBREON_USER_ENVIRONMENT']
FLOW_KIND = 'Flow'


logging.basicConfig(level=logging.INFO)
tracer = trace.get_tracer("operator.flow")


async def listen(umbreon_url: str, reconciler: Coroutine[str, Awaitable[None]]):
    logger = logging.getLogger("listener")

    logger.info(f"Starting listener subscribing to {umbreon_url}")
    async for websocket in websockets.client.connect(umbreon_url):
        logger.info("Acquired connection to umbreon")
        try:
            while True:
                msg = await websocket.recv()

                try:
                    req = json.loads(msg.decode())
                    logger.info("Starting reconciliation")
                    await reconciler(req)
                except Exception:
                    logger.exception("An exception occured during reconciliation")
                else:
                    logger.info("Successfully completed reconciliation")
        except Exception:
            logger.exception("An exception whilst receiving message, reconnecting")


async def reconciler(manifest: dict[str, object]):
    logging.info(f"got reconciliation request for {manifest}")
    traceparent = manifest.get("manifest", {}).get("annotations", {}).get("tracing.otel/traceparent")
    ctx = traceparent and TraceContextTextMapPropagator().extract(carrier={'traceparent': traceparent})

    with tracer.start_as_current_span('reconcile', context=ctx) as span:
        span.set_attribute('name', manifest["name"])


async def main():
    await listen(
        f"ws://{UMBREON_HOST}/watch/{FLOW_KIND}/{UMBREON_PLATFORM_INSTANCE}-{UMBREON_USER_ENVIRONMENT}",
        reconciler
    )
    

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())