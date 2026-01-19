# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在本仓库中工作时提供指导。

## 工作原则

### 基本规范

- **语言要求**:使用简体中文回复用户问题
- **代码质量**:我们的代码会被 Linus Review,要避免被他骂!
- **高标准执行**:重视代码质量、安全性、可维护性
- **国际化**: 所有界面文本必须支持国际化（i18n），严禁硬编码。
- **如果有方案文档输出，就全部输出到./docs/ 目录下。**
- **不明白的地方反问我，先不着急编码**

## 项目概述

IndexTTS2 是 Bilibili 开发的零样本文本转语音合成系统，支持声音克隆、情感控制和多语言合成（中文/英文）。采用三阶段流水线架构：文本处理 → GPT 语义生成 → BigVGAN 声码器。

## 常用命令

所有命令使用 `uv`（必须使用，不要用 pip/conda）：

```bash
# 安装依赖
uv sync --all-extras

# 运行 Web UI（主入口）
uv run webui.py
uv run webui.py --port 7860 --fp16 --deepspeed --cuda_kernel

# 运行脚本（需添加 PYTHONPATH）
PYTHONPATH="$PYTHONPATH:." uv run indextts/infer_v2.py

# 检查 GPU 检测
uv run tools/gpu_check.py

# 运行测试
PYTHONPATH="$PYTHONPATH:." uv run tests/regression_test.py
PYTHONPATH="$PYTHONPATH:." uv run tests/padding_test.py

# 下载模型
hf download IndexTeam/IndexTTS-2 --local-dir=checkpoints
```

## 架构

### 三阶段流水线

1. **文本处理** (`indextts/utils/front.py`)：Unicode 归一化、BPE 分词、拼音支持、词汇表处理
2. **语义生成** (`indextts/gpt/model_v2.py`)：基于 GPT2 的自回归解码器，从文本 + 说话人/情感嵌入生成 8192 个语义码
3. **语音声码** (`indextts/s2mel/` + `indextts/BigVGAN/`)：将语义码转换为梅尔频谱，再通过 BigVGAN 生成波形

### 核心类

- `IndexTTS2` (`indextts/infer_v2.py`)：主推理引擎，处理所有合成模式
- `UnifiedVoice` (`indextts/gpt/model_v2.py`)：基于 GPT 的语义解码器，包含 Conformer 编码器和 Perceiver 重采样器
- `TextNormalizer` / `TextTokenizer` (`indextts/utils/front.py`)：文本预处理流水线

### 情感控制（与说话人解耦）

情感可通过以下方式指定：
- 音频参考文件（`emo_audio_prompt` 参数）
- 8 维浮点向量：`[开心, 愤怒, 悲伤, 恐惧, 厌恶, 忧郁, 惊讶, 平静]`
- 文本描述，使用 Qwen3 编码（`use_emo_text=True`）

### 配置

模型配置位于 `checkpoints/config.yaml`（通过 omegaconf 解析 YAML 格式）。关键参数：
- GPT：1280 维，24 层，20 个注意力头
- 音频：22.05kHz 采样率，1024 FFT
- 语义编解码器：8192 词汇量

## 代码规范

- 推荐所有用户使用 FP16 推理（更快、显存占用更低）
- DeepSpeed 效果因硬件而异
- GPU 支持：CUDA（主要）、XPU（Intel）、MPS（Apple）、CPU 回退
- 平台相关的文本处理：Linux 使用 `WeTextProcessing`，Windows/Mac 使用 `wetext`
- CLI (`indextts/cli.py`) 目前仅支持 v1；v2 CLI 待开发
