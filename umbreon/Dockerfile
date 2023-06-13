FROM python:3.10-slim

ENV OTEL_PYTHON_LOG_CORRELATION=true
WORKDIR /srv

COPY requirements.txt ./
RUN pip install -r requirements.txt && opentelemetry-bootstrap -a install

COPY app.py ./

ENTRYPOINT [ \
    "opentelemetry-instrument", \
    "--service_name", "umbreon", \
    "--traces_exporter", "zipkin_json", \
    "--exporter_zipkin_endpoint", "http://zipkin:9411/api/v2/spans", \
    "--metrics_exporter", "console", \
    "--logs_exporter", "console", \
    "uvicorn", "--host", "0.0.0.0", "--port", "80", "app:app" \
]