<!-- 功能: 文档说明。作用: 提供实现/使用指引。边界: 不包含可执行业务逻辑。 -->

# Skeleton Tasks（基于 architecture.md）

> 目标：在不接入真实 ASR/翻页算法的前提下，先把工程骨架搭起来，确保“可运行、可测试、可扩展”。

---

## Task 01 - 初始化项目骨架与目录

**目标**
- 建立统一目录，保证模块边界清晰、后续可并行开发。

**范围**
- 创建 `src/`、`config/`、`tests/`、`input/`、`output/`、`scripts/`。

**边界（不做）**
- 不引入真实第三方推理依赖。
- 不实现具体算法逻辑。

**产出**
- 项目目录树具备最小结构。

---

## Task 02 - 定义公共数据结构与错误体系

**目标**
- 用统一 schema 和 error code 约束模块输入输出。

**范围**
- `src/common/schema.py`：`TranscriptSegment`、`SlideSpan`。
- `src/common/errors.py`：基础异常与模块异常。

**边界（不做）**
- 不绑定任何具体模型框架异常。

**产出**
- 可复用的数据结构与错误类型。

---

## Task 03 - 搭建配置与日志基础设施

**目标**
- 提供统一配置加载和日志输出入口。

**范围**
- `src/common/config.py`：最小配置对象与加载函数。
- `src/common/logger.py`：统一 logger 工厂。
- `config/default.yaml`、`config/windows_gpu.yaml`。

**边界（不做）**
- 当前阶段不实现完整 YAML 解析与多层覆盖策略。

**产出**
- 可被 pipeline 调用的配置/日志基础能力。

---

## Task 04 - 声明模块接口协议（Interface Contracts）

**目标**
- 在接入真实实现前先冻结关键接口形状，降低后续改动成本。

**范围**
- `src/common/interfaces.py`：ASR/SlideDetector 协议接口。

**边界（不做）**
- 不实现插件注册系统。

**产出**
- 可被 mock/stub 实现复用的接口定义。

---

## Task 05 - 实现 ingest Stub

**目标**
- 打通“输入 → 音频/帧占位产物”路径。

**范围**
- `src/ingest/extract_audio.py`。
- `src/ingest/extract_frames.py`。

**边界（不做）**
- 不调用 FFmpeg/OpenCV。
- 不做视频合法性深入校验。

**产出**
- 占位 `audio.wav` 与 `frame_*.jpg`。

---

## Task 06 - 实现 asr Stub

**目标**
- 在无真实模型时提供稳定、可预测的转写输出。

**范围**
- `src/asr/transcribe.py`。

**边界（不做）**
- 不接入 `faster-whisper`。
- 不做 VAD/降噪。

**产出**
- 固定 `TranscriptSegment` 列表。

---

## Task 07 - 实现 slide_detector Stub

**目标**
- 在无真实翻页检测时输出可用于后续对齐的数据结构。

**范围**
- `src/slide/detect_slides.py`。

**边界（不做）**
- 不做 SSIM/OCR。

**产出**
- 固定 `SlideSpan` 列表。

---

## Task 08 - 实现 aligner 最小逻辑

**目标**
- 实现时间重叠对齐核心函数（可用于单元测试）。

**范围**
- `src/align/align_text.py`：`_overlap` + `align_segments_to_slides`。

**边界（不做）**
- 不做复杂边界回溯/语义匹配。

**产出**
- `page_id -> segments` 映射结果。

---

## Task 09 - 实现 render Stub

**目标**
- 先完成产物出口契约，后续再替换为真实 PDF 渲染。

**范围**
- `src/render/render_pdf.py`。

**边界（不做）**
- 不接入 reportlab/PyMuPDF。

**产出**
- `course_note.pdf` 占位文件。

---

## Task 10 - 实现 M6（orchestrator）入口与阶段编排

**目标**
- 形成可执行主链路（ingest → asr → slide → align → render）。

**范围**
- `src/pipeline/run_pipeline.py`。
- 提供 `main()` CLI 入口与退出码。

**边界（不做）**
- 不做并行调度。
- 不做 checkpoint 恢复。

**产出**
- 一条命令可跑通骨架流程并生成最小产物。

---

## Task 10B - 实现 M7（local_llm_hook）预留 Stub

**目标**
- 为本地 `<20B` API 增强能力预留稳定接口，不影响主链路执行。

**范围**
- 新增 `src/local_llm_hook/hook.py`。
- 在 `run_pipeline.py` 中以配置开关方式调用（默认关闭）。

**边界（不做）**
- 不接入真实本地模型服务。
- 不实现摘要/问答算法。

**产出**
- 可选输出 `local_llm_hook.json` 占位结果。

---

## Task 11 - 建立测试目录与最小测试样例

**目标**
- 先搭测试骨架，确保后续真实逻辑可持续补齐。

**范围**
- `tests/unit/test_align_text.py`。
- `tests/integration/test_pipeline_imports.py`。
- `tests/e2e/test_e2e_contract.md`。

**边界（不做）**
- 当前阶段不跑长视频 E2E。

**产出**
- 可执行/可扩展的测试目录与示例。

---

## Task 12 - 文档与交接规范

**目标**
- 让后续开发者快速接手并替换 stub。

**范围**
- 更新 `architecture.md` / README（后续可补）。
- 明确“哪些文件是 stub，替换顺序是什么”。

**边界（不做）**
- 不编写完整用户手册。

**产出**
- Skeleton 阶段交付说明与替换路线。

---

## 建议执行顺序

1. Task 01 → 04（先定结构/接口）
2. Task 05 → 10（打通主链路）
3. Task 11（补最小测试）
4. Task 12（整理交接）

---

## Skeleton 阶段完成定义（DoD）

- 项目目录结构创建完成。
- `python -m src.pipeline.run_pipeline` 可执行并退出码为 0。
- 生成最小产物：`audio.wav`、`transcript.jsonl`、`page_manifest.json`、`page_text_map.json`、`course_note.pdf`。
- 单元测试样例已存在且可作为后续扩展模板。
- 全部模块仍为 stub，不包含真实模型推理逻辑。
