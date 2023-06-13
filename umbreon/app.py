import json
import logging
import os

import quart
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from redis import asyncio as aioredis


logging.basicConfig(level=logging.INFO)


REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

app = quart.Quart(__name__)
app.asgi_app = OpenTelemetryMiddleware(app.asgi_app)

redis = aioredis.from_url(REDIS_URL, max_connections=10)


def storage_key(kind: str, namespace: str, name: str) -> str:
    return f"umbreon:{kind}:{namespace}:{name}"


@app.put('/object/<kind>/<namespace>/<name>')
async def put_object(kind: str, namespace: str, name: str):
    data = await quart.request.json
    key = storage_key(kind, namespace, name)
    
    async with redis.pipeline(transaction=True) as r:
        r.set(key, json.dumps(data))
        r.publish(key, json.dumps({
            "event": "UPDATE",
            "kind": kind,
            "namespace": namespace,
            "name": name,
            "manifest": data,
        }))
        await r.execute()

    return "", 200, {'content-type': 'text/plain'}


@app.delete('/object/<kind>/<namespace>/<name>')
async def delete_object(kind: str, namespace: str, name: str):
    key = storage_key(kind, namespace, name)
    
    async with redis.pipeline(transaction=True) as r:
        r.delete(key)
        r.publish(key, json.dumps({
            "event": "DELETE",
            "kind": kind,
            "namespace": namespace,
            "name": name,
        }))
        await r.execute()

    return "", 200, {'content-type': 'text/plain'}


@app.get('/object/<kind>/<namespace>/<name>')
async def get_object(kind: str, namespace: str, name: str):
    key = storage_key(kind, namespace, name)
    val = await redis.get(key)
    if val is None:
        return "", 404, {'content-type': 'text/plain'}
    else:
        return val.decode(), 200, {'content-type': 'application/json'}


@app.websocket('/watch/<kind>/<namespace>')
async def watch_kind(kind: str, namespace: str):
    key = storage_key(kind, namespace, "*")
    pconn = aioredis.from_url(REDIS_URL, max_connections=1)
    psub = pconn.pubsub()

    await psub.psubscribe(key)
    await quart.websocket.accept()

    try:
        while True:
            msg = await psub.get_message(ignore_subscribe_messages=True, timeout=10)
            if msg is not None:
                print(msg)
                await quart.websocket.send(msg['data'])
    finally:
        print('shutting down')
        await psub.punsubscribe(key)
        await psub.close()


if __name__ == '__main__':
    app.run(port=6969)
