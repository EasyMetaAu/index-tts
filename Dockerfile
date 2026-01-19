FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    git \
    git-lfs \
    ffmpeg \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && git lfs install

# 安装 uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 复制源代码
COPY indextts/ ./indextts/
COPY webui.py ./
COPY tools/ ./tools/

# 安装依赖
RUN uv sync --all-extras

# 下载模型（使用 ModelScope）
RUN uv tool install modelscope && \
    modelscope download --model IndexTeam/IndexTTS-2 --local_dir ./checkpoints

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s \
    CMD curl -f http://localhost:7860/ || exit 1

ENTRYPOINT ["uv", "run", "webui.py"]
CMD ["--host", "0.0.0.0", "--port", "7860", "--fp16"]
