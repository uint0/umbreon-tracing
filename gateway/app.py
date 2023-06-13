import logging
import os

import quart
from opentelemetry import trace
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
import requests

UMBREON = os.environ.get("UMBREON_URL", 'http://umbreon')

app = quart.Quart(__name__)
app.asgi_app = OpenTelemetryMiddleware(app.asgi_app)


def namespace_for(env, *, platform='brock'):
    return f'{platform}-{env}'


@app.post('/descriptor/register')
async def register():
    body = await quart.request.json
    span_context = trace.get_current_span().context

    env = body['environment']
    descriptor = body['descriptors'][0]

    kind = descriptor['kind']
    name = descriptor['name']

    namespace = namespace_for(env)

    logging.info("Storing descriptor ")

    requests.put(
        f'{UMBREON}/object/{kind}/{namespace}/{name}',
        json={
            'spec': descriptor,
            'kind': kind,
            'name': name,
            'namespace': f'brock-{env}',
            'annotations': {
                'tracing.otel/traceparent': f"00-{span_context.trace_id:032x}-{span_context.span_id:016x}-{span_context.trace_flags:02x}",
            },
        },
    ).raise_for_status()

    return "", 201, {'content-type': 'text/plain'}


@app.get('/descriptor/<env>/<kind>/<name>')
async def descriptor(env: str, kind: str, name: str):
    namespace = namespace_for(env)
    return quart.jsonify(requests.get(
        f'{UMBREON}/object/{kind}/{namespace}/{name}'
    ).json()['spec'])
