# 本地课堂笔记软件方案（视频+音频 → 结构化 PDF）

## 1. 目标拆解

你要做的系统可以拆成两个里程碑：

1. **里程碑 A：本地语音转文字（ASR）**  
   输入课堂视频/音频，输出带时间戳的逐句文本。
2. **里程碑 B：PPT 页级联动笔记**  
   自动检测视频中的 PPT 翻页区间；每一页对应：
   - 左半页：从视频中截取的 PPT 图片
   - 右半页：该页时间区间内的语音转文字

要求是全部本地离线执行，不依赖云端 API。

codex/implement-local-speech-to-text-conversion-25b4oh
### 1.1 约束条件（新增）

- **必须本地运行**：数据处理、转写、对齐、导出全在本机完成，不上传外网。
- **固定 Python 版本**：统一使用 **Python 3.11.x**（建议 3.11.9），避免依赖冲突。
- **必须使用 GPU 加速**：默认走 NVIDIA GPU 推理路径（`faster-whisper + CTranslate2`）。
- **系统适配范围**：优先适配 **Windows 10 / Windows 11**（x64）。
- **可选扩展**：预留本地 `<20B` 模型 API 接口，但不作为 MVP 必选项。


---

## 2. 推荐技术栈（全部本地可运行）

- **FFmpeg**：音视频解复用、抽帧、转码。
- **Whisper 本地模型**（强烈推荐 `faster-whisper + CTranslate2`）：高质量中文转写、可带时间戳。
- **OpenCV**：检测 PPT 页切换（帧差异/结构相似度 SSIM）。
- **PaddleOCR / Tesseract（可选）**：辅助判定是否真的翻页（减少误检）。
- **PyMuPDF / reportlab**：将图片 + 文本拼成 PDF。

> 如果机器有 NVIDIA 显卡，优先用 `faster-whisper + CTranslate2`，并将推理设备固定为 GPU。

---

## 3. 端到端处理流程

### 3.1 预处理

1. 用 FFmpeg 把视频音轨导出为单声道 16k WAV：
   - 统一采样率，减少 ASR 抖动。
2. 从视频按固定帧率抽帧（建议 2~6 fps）：
   - 不需要逐帧，能显著降低计算量。

### 3.2 语音转文字（里程碑 A）

1. 调用本地 Whisper 模型转写音频。
2. 输出段级结构：
   - `start_time`
   - `end_time`
   - `text`
3. 保存为 `transcript.jsonl` 或 `transcript.srt`。

### 3.3 PPT 翻页检测（里程碑 B 核心）

可组合两层策略：

1. **视觉差异阈值**：
   - 比较相邻抽帧的 SSIM / 直方图差异；
   - 差异超过阈值，判定疑似翻页。
2. **OCR 文本变化（可选增强）**：
   - 对疑似翻页帧做 OCR；
   - 若文字块变化明显，提升翻页置信度。

输出页区间：

- `page_id`
- `start_time`
- `end_time`
- `keyframe_path`

### 3.4 页级文本对齐

将 ASR 段按时间戳切分到对应 `page_id`：

- 规则：若 ASR 段与页面时间区间有重叠，则归入该页。
- 可设置最小重叠时长（如 0.3s）避免边界噪声。

### 3.5 生成 PDF（每页左右分栏）

每个 `page_id` 生成一页 PDF：

- 左侧：`keyframe`（按比例缩放，保持不变形）
- 右侧：该页对应转写文本（自动换行、分页）

最终导出：

- `course_note.pdf`
- `page_manifest.json`（记录每页时间区间，便于回溯）

---

## 4. 建议目录结构

```text
project/
  input/
    class.mp4
  output/
    audio.wav
    frames/
    slides/
    transcript.jsonl
    page_manifest.json
    course_note.pdf
  src/
    extract_audio.py
    extract_frames.py
    transcribe.py
    detect_slides.py
    align_text.py
    render_pdf.py
    pipeline.py
```

---

codex/implement-local-speech-to-text-conversion-25b4oh
## 4.1 模块目标（简单版）

1. **ingest（输入预处理）**  
   目标：把 `mp4/mkv` 统一转换为 `16k wav + 2~6 fps` 抽帧结果。

2. **asr（语音转写）**  
   目标：基于 `faster-whisper + CTranslate2` 生成带时间戳文本段。

3. **slide_detector（翻页检测）**  
   目标：输出稳定的页面区间（`page_id/start/end/keyframe`）。

4. **aligner（页文对齐）**  
   目标：将 ASR 文本按时间重叠映射到每个 PPT 页。

5. **pdf_renderer（PDF 拼版）**  
   目标：输出每页“左图右文”的课堂笔记 PDF。

6. **local_llm_hook（预留接口，可选）**  
   目标：预留本地 `<20B` 模型 API 调用位，用于后续摘要/问答增强。

---


## 5. 先做 MVP（两周可落地）

### 第 1 周（先打通主链路）

- 完成音频抽取 + Whisper 转写 + JSON 输出。
- 用简单帧差阈值做翻页检测。
- 按时间将文本分配到页面。

### 第 2 周（输出可交付结果）

- 生成左右分栏 PDF。
- 增加阈值配置与可视化检查（抽样预览翻页点）。
- 调整中文标点与断句，提高阅读体验。

---

## 6. 关键难点与规避策略

1. **老师走动/摄像头抖动导致误翻页**  
   解决：先裁剪 PPT 区域（ROI），只在该区域做差异检测。

2. **动画逐条出现被误判成多页**  
   解决：设置“最短页时长”（如 >= 8 秒）和“翻页冷却时间”（如 2 秒）。

3. **课堂噪声影响转写**  
   解决：加 VAD（语音活动检测）+ 降噪预处理；必要时提高模型规格（`medium`）。

4. **ASR 时间戳偏移**  
   解决：对齐前做 1~2 秒容忍窗口，或用关键词二次对齐。

---

## 7. 性能建议

- 2 小时课程建议分块处理（例如每 20 分钟一个 chunk）。
- 抽帧率建议从 2 fps 起步，在 2~6 fps 之间按课程内容复杂度调整。
- 推理优先 GPU（NVIDIA 场景默认启用）；无 GPU 时可选 `small` 模型保证可用速度。

---

## 8. 质量评估指标（建议最小集）

- **ASR 可读性**：抽样人工评估 30 段，统计可理解率。
- **翻页准确率**：
  - Precision：检测到的翻页中有多少是真翻页
  - Recall：真实翻页中有多少被检测到
- **页文对齐满意度**：随机抽 20 页，检查文字是否属于该页内容。

---

## 9. 可扩展方向（后续）

- 自动生成“本页关键词 / 小结”。
- 同步导出 Markdown（支持 Obsidian/Notion）。
- 建立全文检索索引（按页跳转到视频时间点）。
- 预留本地 `<20B` 模型 API 调用层（可选），用于后续做章节摘要、术语规范化和问答增强。

---

## 10. 一句话实现路线

先做“**ASR + 简单翻页检测 + 页级 PDF 拼版**”的最小闭环；跑通后再优化翻页准确率与文本可读性。
 codex/implement-local-speech-to-text-conversion-25b4oh

---

## 11. 简单验收标准（MVP）

满足以下 6 条即可判定 MVP 验收通过：

1. 在 **Windows 10/11 + Python 3.11.x** 环境可一键跑通主流程。
2. 默认使用 GPU 路径完成转写（日志中可看到 CUDA/GPU 设备信息）。
3. 输入 1 个课堂视频后，可输出 `transcript.jsonl`（含 `start/end/text`）。
4. 可输出 `page_manifest.json`（含 `page_id/start/end/keyframe_path`）。
5. 可输出 `course_note.pdf`，并满足“每页左图右文”排版。
6. 全流程不依赖外部云 API（断网环境可执行）。

