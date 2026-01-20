"""
Standalone API server for IndexTTS2.

This script provides a REST API without the WebUI. Useful for production
deployments where only API access is needed.

Usage:
    uv run api.py --port 8000 --fp16
"""

import os
import sys

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, "indextts"))

import argparse

parser = argparse.ArgumentParser(
    description="IndexTTS2 API Server",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument("--port", type=int, default=8000, help="Port to run the API server on")
parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind the API server to")
parser.add_argument("--model_dir", type=str, default="./checkpoints", help="Model checkpoints directory")
parser.add_argument("--fp16", action="store_true", default=False, help="Use FP16 for inference if available")
parser.add_argument("--deepspeed", action="store_true", default=False, help="Use DeepSpeed to accelerate if available")
parser.add_argument("--cuda_kernel", action="store_true", default=False, help="Use CUDA kernel for inference if available")
cmd_args = parser.parse_args()

if not os.path.exists(cmd_args.model_dir):
    print(f"Model directory {cmd_args.model_dir} does not exist. Please download the model first.")
    sys.exit(1)

for file in [
    "bpe.model",
    "gpt.pth",
    "config.yaml",
    "s2mel.pth",
    "wav2vec2bert_stats.pt"
]:
    file_path = os.path.join(cmd_args.model_dir, file)
    if not os.path.exists(file_path):
        print(f"Required file {file_path} does not exist. Please download it.")
        sys.exit(1)

import uvicorn
from indextts.infer_v2 import IndexTTS2
from indextts.api import create_api_app

print(">> Loading IndexTTS2 model...")
tts = IndexTTS2(
    model_dir=cmd_args.model_dir,
    cfg_path=os.path.join(cmd_args.model_dir, "config.yaml"),
    use_fp16=cmd_args.fp16,
    use_deepspeed=cmd_args.deepspeed,
    use_cuda_kernel=cmd_args.cuda_kernel,
)

os.makedirs("outputs/tasks", exist_ok=True)

app = create_api_app(tts)

if __name__ == "__main__":
    print(f">> Starting API server on http://{cmd_args.host}:{cmd_args.port}")
    print(f">> API documentation available at http://{cmd_args.host}:{cmd_args.port}/docs")
    uvicorn.run(app, host=cmd_args.host, port=cmd_args.port)
