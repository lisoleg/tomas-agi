# TOMAS LLM Router + EML Injector 升级报告
# TOMAS 多模型智能路由升级 — 交付报告

> 基于章锋《开源大模型军备竞赛下的 TOMAS 战略》(2026-06-15) 实现

---

## TL;DR

将 TOMAS/太极OS 从**单一 DeepSeek 绑定**升级为**12 家开源模型按任务类型智能路由**的多模型架构，LLM 只是"舌头"，EML + 死零/MUS 才是"大脑"。

---

## 交付概览

| 指标 | 数值 |
|------|------|
| 交付状态 | ✅ 完成 |
| 新增/修改文件 | 4 新文件 + 1 修改 |
| 测试通过率 | 47/47 (7+20+27) |
| 向后兼容性 | ✅ `--llm` 参数继续工作 |
| 新增命令行参数 | 3 个 (`--router`, `--router-config`, `--task-type`) |

---

## 交付文件清单

### 新增文件

| 文件 | 行数 | 职责 |
|------|------|------|
| `sim/model_pool.json` | ~120 | 12 家模型池配置（含 Miro-Med） |
| `sim/eml_injector.py` | ~180 | EML 执行上下文注入器（v2.0） |
| `sim/router.py` | ~330 | TOMAS 多模型路由器 |
| `tests/test_router.py` | ~270 | Router + Injector 测试套件（27 cases） |

### 修改文件

| 文件 | 改动说明 |
|------|----------|
| `sim/token_bridge.py` | 新增 `set_router()`, `_creative_respond_router()`, `--router`/`--task-type` CLI 参数 |

### 配置更新

| 文件 | 改动说明 |
|------|----------|
| `sim/.env` | 追加 12 家模型 API Key 占位符 |

---

## 核心架构升级

### 之前（单一模型）

```
用户查询 → InferenceEngine → CreativeEngine(DeepSeek only) → 响应
```

### 现在（多模型路由）

```
用户查询 → InferenceEngine
  ├─ 高置信度 → TokenBridge 翻译官（模板/LSTM）
  └─ 低置信度 → TOMASRouter.route(task_type)
       ├─ task_type=reason       → DeepSeek V3 (通用推理)
       ├─ task_type=long_extract → GLM-5 (1M ctx 长文抽边)
       ├─ task_type=code_gen     → DeepSeek/Kimi-K2 (代码生成)
       ├─ task_type=med_annotate → Miro-Med-70B (医学标注)
       ├─ task_type=academic    → InternLM (数理 EML)
       ├─ task_type=rag          → Command-R (检索增强)
       ├─ task_type=multilingual → Qwen3 (多语对照)
       └─ 未知 task_type        → DeepSeek (fallback)
```

每个 LLM 调用都注入 **EML 执行上下文 v2.0**：
```
# TOMAS EML Execution Context (v2.0)
- κ (Spectral Fold Depth): 4.0
- Dead-Zero Threshold (θ_dead): 0.15
  → If I(e) < θ_dead ⇒ Output [DEAD_ZERO_REJECT: Reason]
- MUS Tags Active: Asym≠0 double-exist
  → If paradox pair detected (Asym≠0) ⇒ Output [MUS_ACTIVE: <pair>]
```

---

## 12 家模型全景

| # | 模型 | 角色 | 启用状态 |
|---|------|------|----------|
| 1 | **DeepSeek V3** | 主推理核（Proto-L3 Mirror） | ✅ 已启用 |
| 2 | **Qwen3-235B** | 多语 EML | ⏳ 待配置 API Key |
| 3 | **GLM-5-Pro** | 长文 EML 抽边（1M ctx） | ⏳ 待配置 |
| 4 | **Kimi-K2-Code** | 代码生成（GPCT/ITC 伪码） | ⏳ 待配置 |
| 5 | **MiniMax-M3** | Agentic 预解析 | ⏳ 待权重开源 |
| 6 | **Llama-4-Scout** | 西文学术 EML | ⏳ 待配置 |
| 7 | **Command-R-Plus** | RAG-EML（检索增强） | ⏳ 待配置 |
| 8 | **Mistral-Large-2** | 轻量备选 / 端侧伴生 | ⏳ 待配置 |
| 9 | **Gemma-3-27B** | 教育/轻量 EML 初标 | ⏳ 待配置 |
| 10 | **Miro-Med-70B (TCCI)** | 脏腑-神经-精神 EML 初标（黄金） | ⏳ 待配置 |
| 11 | **InternLM-2.5-20B** | 学术/数理 EML | ⏳ 待配置 |
| 12 | **Yi-1.5-34B** | 中英文 EML 对照 | ⏳ 待配置 |

---

## 使用方式

### 快速开始（推荐）

```bash
# 启用 Router（自动加载 model_pool.json）
python token_bridge.py --load data/physics_distilled.eml \
       --query "量子纠缠的本质是什么？" \
       --router --task-type reason
```

### 医学标注（Miro-Med）

```bash
# 需先配置 MIROMED_API_KEY 环境变量
python token_bridge.py --load data/medicine_distilled.eml \
       --query "心肾不交如何辨证？" \
       --router --task-type med_annotate
```

### 长文抽边（GLM-5）

```bash
# 需先配置 GLM5_API_KEY
python token_bridge.py --load data/physics_distilled.eml \
       --query "从《黄帝内经》中提取五行相生关系" \
       --router --task-type long_extract
```

### 向后兼容（旧用法仍可用）

```bash
python token_bridge.py --load data/physics_distilled.eml \
       --query "量子计算" --llm --api-key sk-xxx
```

---

## 测试覆盖

```
tests/test_token_bridge.py  ... 7 passed, 4 skipped
tests/test_eml_dimred.py    ... 20 passed
tests/test_router.py        ... 27 passed
=========================================
总计 47 passed, 4 skipped  ✅ 零回归
```

---

## 技术亮点

1. **模型解耦**：LLM 调用统一收口到 `TOMASRouter._call_llm()`，OpenAI 兼容格式，切换模型零代码改动
2. **EML 注入自动化**：每次 LLM 调用自动注入 κ/θ_dead/MUS Tags，无需手动构造 prompt
3. **FPT 保证**：数学降维四合一（ITC→GPCT→Brown-Miklós→Matroid）保证 k≤参数，推理复杂度从 NP-hard 落入 FPT 区
4. **向后兼容**：`--llm` 参数继续工作，老用户无感升级
5. **零依赖增加**：复用现有 `requests` 库，不引入新依赖

---

## 下一步建议

1. **配置至少 2 个 API Key**（DeepSeek + 任一个其他模型）以验证路由切换
2. **运行端到端测试**：用 `--router` 跑一个完整查询，观察 Router 日志输出
3. **扩展前端**：`deepseek-chat/` 前端的 `TokenBridgeClient` 也需支持 Router 模式（当前硬编码 DeepSeek API）
4. **T-Processor 映射**：将 Router 的模型选择逻辑映射到 T-Processor 忆阻芯片的 Crossbar 阵列配置

---

*交付完成时间：2026-06-15 20:10 GMT+8*  
*实现者：寇豆码（Kou）· 工程师 | 主理人：齐活林（Qi）· 交付总监*
