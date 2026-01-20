FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
# HuggingFace 镜像（解决中国大陆访问超时问题）
ENV HF_ENDPOINT=https://hf-mirror.com
# HuggingFace 下载进度条
ENV HF_HUB_DISABLE_PROGRESS_BARS=0

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    git \
    git-lfs \
    ffmpeg \
    libsndfile1 \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && git lfs install

# 安装 uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# 复制依赖文件
COPY pyproject.toml uv.lock README.md ./

# 复制源代码
COPY indextts/ ./indextts/
COPY webui.py api.py ./
COPY tools/ ./tools/
COPY examples/ ./examples/

# 安装依赖
# DS_BUILD_OPS=0: 跳过 deepspeed CUDA ops 编译（runtime 镜像无 nvcc）
ENV DS_BUILD_OPS=0
RUN uv sync --all-extras

# 安装 modelscope CLI（用于启动时下载模型）
RUN uv tool install modelscope

# 复制启动脚本
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 7861

HEALTHCHECK --interval=30s --timeout=10s \
    CMD curl -f http://localhost:7861/api/v1/health || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["--host", "0.0.0.0", "--port", "7861", "--fp16"]
