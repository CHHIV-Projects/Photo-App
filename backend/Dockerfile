# syntax=docker/dockerfile:1

FROM python:3.11.9-slim-bookworm AS system

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        libimage-exiftool-perl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements*.txt ./

FROM system AS dependencies-cpu
RUN python -m pip install --requirement requirements-linux-cpu.txt

FROM system AS dependencies-gpu
RUN python -m pip install --requirement requirements-linux-gpu.txt

FROM dependencies-cpu AS development-cpu
RUN python -m venv /opt/photo-organizer-icloud \
    && /opt/photo-organizer-icloud/bin/python -m pip install --requirement requirements-icloud-development.txt \
    && /opt/photo-organizer-icloud/bin/python -c "import importlib.metadata as m; from pyicloud_ipd.base import PyiCloudService; assert m.version('icloudpd') == '1.32.3'"
COPY app ./app
COPY scripts ./scripts
RUN python scripts/provision_yunet_model.py \
    && groupadd --system photo-organizer \
    && useradd --system --gid photo-organizer --home-dir /app photo-organizer \
    && mkdir -p /app/storage/acquisition/windows /app/icloud-auth \
    && chmod 0700 /app/icloud-auth \
    && chown -R photo-organizer:photo-organizer /app
USER photo-organizer
EXPOSE 8001
HEALTHCHECK --interval=15s --timeout=8s --start-period=90s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=5)"]
CMD ["python", "scripts/container_entrypoint.py"]

FROM dependencies-gpu AS development-gpu
RUN python -m venv /opt/photo-organizer-icloud \
    && /opt/photo-organizer-icloud/bin/python -m pip install --requirement requirements-icloud-development.txt \
    && /opt/photo-organizer-icloud/bin/python -c "import importlib.metadata as m; from pyicloud_ipd.base import PyiCloudService; assert m.version('icloudpd') == '1.32.3'"
COPY app ./app
COPY scripts ./scripts
RUN python scripts/provision_yunet_model.py \
    && groupadd --system photo-organizer \
    && useradd --system --gid photo-organizer --home-dir /app photo-organizer \
    && mkdir -p /app/storage/acquisition/windows /app/icloud-auth \
    && chmod 0700 /app/icloud-auth \
    && chown -R photo-organizer:photo-organizer /app
USER photo-organizer
EXPOSE 8001
HEALTHCHECK --interval=15s --timeout=8s --start-period=90s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=5)"]
CMD ["python", "scripts/container_entrypoint.py"]
