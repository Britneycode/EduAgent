# EduAgent 后端镜像
# Python 3.12 + uv 管理依赖，内置 BGE 中文 Embedding 模型
# 构建（在项目根目录执行）：docker compose -f docker-compose.prod.yml build backend

# ---------- 构建阶段 ----------
FROM python:3.12-slim AS builder

# 阿里云 PyPI 镜像，加速中国大陆服务器构建
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    UV_INDEX_URL=${PIP_INDEX_URL} \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN pip install --no-cache-dir uv

WORKDIR /app

# 先只拷贝依赖清单，利用 Docker 层缓存
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 将 CUDA 版 PyTorch 替换为 CPU 版并清理 NVIDIA 依赖（镜像可缩小约 4GB）
# 若下载失败则保留完整 CUDA 版（镜像更大，但功能不受影响）
RUN uv pip install --python /app/.venv/bin/python \
        --index-url https://download.pytorch.org/whl/cpu torch \
    && (uv pip list --python /app/.venv/bin/python --format=freeze \
        | grep -iE '^(nvidia-|triton)' | cut -d= -f1 \
        | xargs -r uv pip uninstall --python /app/.venv/bin/python) \
    || echo "警告：CPU 版 PyTorch 替换失败，保留默认版本"

# ---------- 运行阶段 ----------
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}" \
    # HuggingFace 国内镜像，避免模型下载失败
    HF_ENDPOINT=https://hf-mirror.com \
    HF_HOME=/app/.cache/huggingface

WORKDIR /app

COPY --from=builder /app/.venv ./.venv
COPY app ./app
COPY knowledge ./knowledge

# 构建期预下载 BGE Embedding 模型（约 100MB），避免首次启动时联网下载
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')" \
    || echo "警告：模型预下载失败，将在首次启动时自动重试下载"

# 数据目录：SQLite 数据库 / Chroma 向量库 / 生成资产，运行时挂载卷持久化
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000

# 单 worker：SQLite 与进程内缓存不适用于多进程
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
