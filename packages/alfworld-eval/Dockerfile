# alfworld-eval sandbox image: text-only ALFWorld evaluation harness
# (vanilla / skillopt / trace2skill / skillrl protocol). Used as an e2b
# "custom sandbox" image for multi-sandbox sharded evaluation runs.
#
# alfworld==0.4.2 / textworld[pddl]==1.6.2 do not ship linux/amd64 wheels
# for every dependency, so build tools are kept in the builder stage.
# Build with:
#   docker buildx build --platform linux/amd64 \
#     --build-context wheels=.wheels-cache \
#     -t alfworld-eval:local --load .

FROM --platform=linux/amd64 python:3.11-slim-bookworm AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple

# deb.debian.org is extremely slow from this network; use Tencent's mirror instead.
RUN sed -i 's|deb.debian.org|mirrors.tencent.com|g; s|security.debian.org|mirrors.tencent.com/debian-security|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|deb.debian.org|mirrors.tencent.com|g; s|security.debian.org|mirrors.tencent.com/debian-security|g' /etc/apt/sources.list 2>/dev/null || true

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git \
    build-essential cmake pkg-config \
    libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /opt/alfworld-eval
COPY . .

# spacy's dependency tree (numpy/spacy/thinc/blis/...) downloads extremely
# slowly over this network from inside the emulated linux/amd64 container,
# even via mirrors. Pre-fetched (full dependency closure) on the host via
# an emulated container talking to a fast mirror, then installed directly
# into the venv here so `uv sync` below finds them already satisfied.
# textworld/jericho are left to `uv sync` -- they need build-essential (cmake/make)
# to compile from sdist, which is fast and doesn't need network beyond a small download.
# Pulled from a separate build context (not the main one) so the ~48MB wheel
# cache never becomes part of the final image's layer history.
RUN --mount=type=bind,from=wheels,target=/wheels-cache \
    uv venv .venv && \
    uv pip install --python .venv/bin/python --no-index --find-links /wheels-cache \
    blis numpy pydantic-core pygments spacy srsly thinc networkx
RUN uv sync --frozen --no-dev

FROM --platform=linux/amd64 python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/alfworld-eval/.venv/bin:$PATH \
    ALFWORLD_DATA=/opt/alfworld-eval/.data/alfworld

# deb.debian.org is extremely slow from this network; use Tencent's mirror instead.
RUN sed -i 's|deb.debian.org|mirrors.tencent.com|g; s|security.debian.org|mirrors.tencent.com/debian-security|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|deb.debian.org|mirrors.tencent.com|g; s|security.debian.org|mirrors.tencent.com/debian-security|g' /etc/apt/sources.list 2>/dev/null || true

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/alfworld-eval
COPY --from=builder /opt/alfworld-eval/.venv ./.venv
COPY . .

# e2b needs a non-root "user" account to exist on custom sandbox images.
RUN useradd --shell /bin/bash --create-home user && \
    echo "user ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    chown -R user:user /opt/alfworld-eval

CMD ["/bin/sh", "-c", "sleep infinity"]
