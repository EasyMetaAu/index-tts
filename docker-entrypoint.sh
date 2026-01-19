#!/bin/bash
set -e

# 检测模型是否存在（检测 bpe.model，这是 webui.py 首先检测的文件）
if [ ! -f "/app/checkpoints/bpe.model" ]; then
    echo "Models not found, downloading from ModelScope..."
    modelscope download --model IndexTeam/IndexTTS-2 --local_dir /app/checkpoints
    echo "Models downloaded successfully."
fi

# 执行原始命令
exec uv run webui.py "$@"
