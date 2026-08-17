FROM python:3.11.13-slim-bookworm
WORKDIR /app
COPY src /app/src
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    RUNTIME_STATE_ROOT=/var/lib/eth-macro-data-bridge \
    D8_INTERNAL_PORT=8080
RUN groupadd --gid 10001 d8 && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin d8 \
    && mkdir -p /var/lib/eth-macro-data-bridge \
    && chown -R 10001:10001 /var/lib/eth-macro-data-bridge /app
USER 10001:10001
VOLUME ["/var/lib/eth-macro-data-bridge"]
EXPOSE 8080
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD ["python","-c","import json,os,urllib.request; t=os.getenv('D8_RUNTIME_TOKEN'); h={'Authorization':'Bearer '+t} if t else {}; r=urllib.request.Request('http://127.0.0.1:8080/v1/health',headers=h); d=json.load(urllib.request.urlopen(r,timeout=2)); raise SystemExit(0 if d.get('status')=='PASS' else 1)"]
CMD ["python","-m","d8_service"]
