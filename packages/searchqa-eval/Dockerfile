# searchqa-eval sandbox image: unified single-turn SearchQA evaluation
# (SkillOpt / Trace2Skill protocol). Used as an e2b "custom sandbox" image
# for multi-sandbox sharded evaluation runs.
FROM --platform=linux/amd64 python:3.11-slim-bookworm

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
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /opt/searchqa-eval
COPY . .
RUN uv sync --frozen --no-dev

# e2b needs a non-root "user" account to exist on custom sandbox images.
RUN useradd --shell /bin/bash --create-home user && \
    echo "user ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    chown -R user:user /opt/searchqa-eval

CMD ["/bin/sh", "-c", "sleep infinity"]
