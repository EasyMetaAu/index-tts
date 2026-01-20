#!/bin/bash
set -e

# HuggingFace 缓存目录（与 infer_v2.py 中的 HF_HUB_CACHE 一致）
export HF_HUB_CACHE="/app/checkpoints/hf_cache"

# 创建缓存目录（如果不存在）
mkdir -p "$HF_HUB_CACHE"

# 检测主模型是否存在（检测 bpe.model，这是 webui.py 首先检测的文件）
if [ ! -f "/app/checkpoints/bpe.model" ]; then
    echo "Models not found, downloading from ModelScope..."
    modelscope download --model IndexTeam/IndexTTS-2 --local_dir /app/checkpoints
    echo "Models downloaded successfully."
fi

# 预下载 HuggingFace 模型（避免运行时超时）
echo "Checking HuggingFace models..."
echo "Cache directory: $HF_HUB_CACHE"
ls -la "$HF_HUB_CACHE" 2>/dev/null || echo "(empty or not accessible)"

# 1. facebook/w2v-bert-2.0 (SeamlessM4TFeatureExtractor)
W2V_SNAPSHOT="$HF_HUB_CACHE/models--facebook--w2v-bert-2.0/snapshots"
if [ ! -d "$W2V_SNAPSHOT" ] || [ -z "$(ls -A "$W2V_SNAPSHOT" 2>/dev/null)" ]; then
    echo "Downloading facebook/w2v-bert-2.0..."
    uv run hf download facebook/w2v-bert-2.0 --cache-dir "$HF_HUB_CACHE" || echo "Warning: Failed to download w2v-bert-2.0, will retry at runtime"
else
    echo "facebook/w2v-bert-2.0: cached"
fi

# 2. amphion/MaskGCT (semantic_codec)
MASKGCT_SNAPSHOT="$HF_HUB_CACHE/models--amphion--MaskGCT/snapshots"
if [ ! -d "$MASKGCT_SNAPSHOT" ] || [ -z "$(ls -A "$MASKGCT_SNAPSHOT" 2>/dev/null)" ]; then
    echo "Downloading amphion/MaskGCT semantic_codec..."
    uv run hf download amphion/MaskGCT semantic_codec/model.safetensors --cache-dir "$HF_HUB_CACHE" || echo "Warning: Failed to download MaskGCT, will retry at runtime"
else
    echo "amphion/MaskGCT: cached"
fi

echo "HuggingFace models check complete."

# 执行原始命令（默认启用 API）
exec uv run webui.py --enable_api "$@"
