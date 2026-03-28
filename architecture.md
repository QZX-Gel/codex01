# 课堂笔记系统架构说明（Architecture）

> 基于 `LOCAL_CLASSNOTE_PLAN.md` 的工程化落地文档，重点强调：**模块划分、目录结构、核心接口、数据流、配置/日志/异常/测试、Open Questions**。  
> 目标是让团队可以直接按此拆分开发任务并并行实现。

---

## 1. 架构目标与边界

### 1.1 架构目标

- 全流程本地离线运行（不依赖云 API）。
- Python 3.11.x 固定运行时，优先支持 Windows 10/11。
- 默认走 NVIDIA GPU 路径做 ASR（`faster-whisper + CTranslate2`）。
- 输出可审计的中间产物：`transcript.jsonl`、`page_manifest.json`、`course_note.pdf`。
- 支持后续预留本地 `<20B` 模型 API 增强能力（摘要/问答）。

### 1.2 非目标（当前阶段）

- 不做在线协作编辑。
- 不做跨平台 GUI（先 CLI 可用）。
- 不做复杂的多路视频源自动融合。

---

## 2. 模块划分（核心）

> 采用“管道式 + 产物落盘”的模块化设计。每个模块输入/输出清晰，可独立测试。

### M1. `ingest`（输入预处理）

**职责**
- 校验输入视频文件。
- 抽取音频（16k mono wav）。
- 抽帧（默认 2~6 FPS，可配置）。

**输入**
- `input/class.mp4`

**输出**
- `output/audio.wav`
- `output/frames/frame_*.jpg`
- `output/meta/video_info.json`

---

### M2. `asr`（语音转写）

**职责**
- 调用 `faster-whisper + CTranslate2` 本地模型。
- 产出带时间戳分段转写。

**输入**
- `output/audio.wav`

**输出**
- `output/transcript.jsonl`
- `output/transcript.srt`（可选）

---

### M3. `slide_detector`（翻页检测）

**职责**
- 基于帧差/SSIM 做疑似翻页检测。
- （可选）OCR 二次确认，降低误检。
- 生成页面时间区间与关键帧。

**输入**
- `output/frames/*.jpg`

**输出**
- `output/slides/keyframe_*.jpg`
- `output/page_manifest.json`

---

### M4. `aligner`（页文对齐）

**职责**
- 将 ASR 分段按时间重叠映射到页面区间。
- 处理边界段（最小重叠阈值、容忍窗口）。

**输入**
- `output/transcript.jsonl`
- `output/page_manifest.json`

**输出**
- `output/page_text_map.json`

---

### M5. `pdf_renderer`（笔记导出）

**职责**
- 按“左图右文”布局渲染每页。
- 合并导出课程笔记 PDF。

**输入**
- `output/slides/keyframe_*.jpg`
- `output/page_text_map.json`

**输出**
- `output/course_note.pdf`

---

M6. orchestrator（pipeline orchestration）

职责

构建并执行整体 pipeline（按阶段顺序调度）。
管理阶段依赖、失败退出与重试策略。
支持仅运行某阶段（--only）与断点续跑（--resume）。
汇总运行状态并生成统一退出码。

输入

config/default.yaml / user config YAML
CLI runtime args
--input
--output-dir
--only <stage>
--resume-from <stage>
--force
--enable-llm
output/meta/checkpoint.json（若存在）
各阶段既有产物的存在性与 schema 校验结果

输出

output/meta/run_plan.json
output/meta/checkpoint.json
output/meta/run_summary.json
output/logs/run.log
process exit code
0: success
1: config / input error
2: stage execution failure
3: partial success / interrupte

M7. local_llm_hook（optional extension）

职责

提供可插拔的本地 LLM 接入口。
用于可选后处理（如摘要、术语规范、索引增强）。
不参与核心 pipeline，按需启用。

输入

output/page_text_map.json
config/llm.yaml（可选）
prompt templates（可选）
prompts/page_summary.txt
prompts/term_normalize.txt
prompts/qa_index.txt

输出（可选）

output/page_summary.json
output/term_map.json
output/qa_index.json
output/logs/llm_hook.log

## 3. 目录结构（建议）

```text
project/
  input/
    class.mp4

  output/
    audio.wav
    frames/
    slides/
    meta/
      video_info.json
    transcript.jsonl
    transcript.srt
    page_manifest.json
    page_text_map.json
    course_note.pdf
    logs/
      run.log

  src/
    ingest/
      extract_audio.py
      extract_frames.py
    asr/
      transcribe.py
    slide/
      detect_slides.py
    align/
      align_text.py
    render/
      render_pdf.py
    pipeline/
      run_pipeline.py
      checkpoint.py
    common/
      config.py
      logger.py
      schema.py
      errors.py

  config/
    default.yaml
    windows_gpu.yaml

  tests/
    unit/
    integration/
    e2e/
```

---

## 4. 核心接口（建议草案）

> 以下是 Python 层面的“最小接口”，用于解耦模块。

```python
# src/common/schema.py
from dataclasses import dataclass

@dataclass
class TranscriptSegment:
    start_time: float
    end_time: float
    text: str

@dataclass
class SlideSpan:
    page_id: int
    start_time: float
    end_time: float
    keyframe_path: str
```

```python
# ingest

def extract_audio(video_path: str, out_wav: str, sr: int = 16000) -> str: ...
def extract_frames(video_path: str, out_dir: str, fps: float) -> list[str]: ...

# asr

def transcribe_audio(wav_path: str, model_name: str, device: str) -> list[TranscriptSegment]: ...

# slide_detector

def detect_slide_spans(frame_paths: list[str], ssim_threshold: float) -> list[SlideSpan]: ...

# aligner

def align_segments_to_slides(
    segments: list[TranscriptSegment],
    slides: list[SlideSpan],
    min_overlap_sec: float = 0.3,
) -> dict[int, list[TranscriptSegment]]: ...

# pdf_renderer

def render_note_pdf(slides: list[SlideSpan], page_text_map: dict[int, list[TranscriptSegment]], out_pdf: str) -> str: ...

# orchestrator

def run_pipeline(config_path: str) -> int: ...
```

---

## 5. 数据流（Data Flow）

```text
[输入视频]
   │
   ├─ M1 ingest
   │   ├─ audio.wav
   │   └─ frames/*.jpg
   │
   ├─ M2 asr
   │   └─ transcript.jsonl
   │
   ├─ M3 slide_detector
   │   └─ page_manifest.json + keyframe_*.jpg
   │
   ├─ M4 aligner
   │   └─ page_text_map.json
   │
   ├─ M5 pdf_renderer
   │   └─ course_note.pdf
   │
   └─ M6 orchestrator
       └─ logs/run.log + exit code
```

### 5.1 数据格式建议

- `transcript.jsonl`：每行一个转写段，字段：`start_time/end_time/text`。
- `page_manifest.json`：数组，字段：`page_id/start_time/end_time/keyframe_path`。
- `page_text_map.json`：`{page_id: [segments...]}`。

---

## 6. 配置 / 日志 / 异常 / 测试

### 6.1 配置（Config）

建议 YAML + 环境变量覆盖：

- 运行环境：`python_version=3.11.x`、`platform=win10+`
- ASR：`model_name`、`device=cuda/cpu`、`beam_size`
- 抽帧：`fps=2~6`
- 翻页：`ssim_threshold`、`min_page_duration_sec`、`cooldown_sec`
- 对齐：`min_overlap_sec`、`boundary_tolerance_sec`
- 输出：`output_dir`、`save_intermediate=true`

示例：

```yaml
runtime:
  python_version: "3.11"
  platform: "windows"

asr:
  engine: "faster-whisper"
  model_name: "medium"
  device: "cuda"

video:
  frame_fps: 4

slide:
  ssim_threshold: 0.82
  min_page_duration_sec: 8
  cooldown_sec: 2

align:
  min_overlap_sec: 0.3
  boundary_tolerance_sec: 1.0
```

### 6.2 日志（Logging）

- 使用结构化日志（JSON 或 key-value）。
- 每个模块统一打印：`module`, `stage`, `input`, `output`, `duration_ms`, `status`。
- 关键事件：
  - GPU 是否可用、实际 device。
  - 翻页数量、过滤后的页面数量。
  - 各阶段耗时。

### 6.3 异常（Error Handling）

定义分层异常码（建议）：

- `E1001` 输入文件不存在/损坏
- `E2001` FFmpeg 调用失败
- `E3001` ASR 模型加载失败（GPU/驱动不匹配）
- `E4001` 翻页结果为空（阈值异常）
- `E5001` PDF 渲染失败（字体/编码）

策略：

- 模块内抛业务异常；`orchestrator` 统一捕获并输出最终错误码。
- 所有失败必须带修复建议（例如“降低 fps / 调整 ssim 阈值 / 切换 cpu 模式”）。

### 6.4 测试（Testing）

**单元测试（unit）**
- 时间重叠计算函数。
- 页文对齐边界条件。
- 配置加载与默认值覆盖。

**集成测试（integration）**
- `ingest -> asr`。
- `slide_detector -> aligner`。
- `aligner -> pdf_renderer`。

**端到端测试（e2e）**
- 5~10 分钟样例课程视频跑全链路。
- 校验产物存在且 schema 合法。
- 校验输出 PDF 页数与 page_manifest 一致。

---

## 7. Open Questions（待确认项）

1. **PPT ROI 获取方式**：手工框选、自动检测，还是半自动？
2. **ASR 模型默认档位**：`small`（快）还是 `medium`（准）？
3. **多语言课堂**：是否要自动语言检测与分语言输出？
4. **动画频繁课件**：是否引入“文本相似度”辅助翻页合并？
5. **本地 `<20B` API 协议**：统一采用 OpenAI-compatible 还是自定义协议？
6. **PDF 版式策略**：固定左右 5:5，还是按图片比例自适应？
7. **字体与编码**：Windows 默认中文字体选型（宋体/微软雅黑）如何统一？

---

## 8. 建议的下一步

- 第一步：按本文件先落 `src/common/schema.py` 与 `config/default.yaml`。
- 第二步：优先实现 `M1 -> M2 -> M4 -> M5` 最短闭环（先不做 OCR 增强）。
- 第三步：加入 `M3` 的 OCR 二次确认与阈值调优工具。
- 第四步：补齐 `tests/e2e` 与 MVP 验收脚本。
