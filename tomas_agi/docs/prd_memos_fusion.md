# PRD：TOMAS-MemOS 融合层

**版本**：v1.0  
**日期**：2026-06-16  
**作者**：齐活林（Qi）· 交付总监  

---

## 1. 产品目标

| # | 目标 | 优先级 |
|---|------|--------|
| G1 | 实现死零校验（Dead-Zero Check），防止低 ℐ 值幻觉写入长期记忆 | P0 |
| G2 | 实现 MUS 双存机制，支持矛盾记忆共存而非覆盖 | P0 |
| G3 | 实现 ψ-锚（Self-Snapshot），让记忆携带"我感" | P0 |
| G4 | 实现 κ-Gate 激活，按语境深度选择性激活记忆 | P1 |
| G5 | 提供 TOMAS_MemOS_Fusion 统一接口，兼容现有 token_bridge 推理流程 | P0 |

---

## 2. 用户故事

| # | 角色 | 故事 |
|---|------|------|
| US1 | 系统（记忆写入者） | 当用户输入"太阳绕地球转"时，系统应拒绝写入长期记忆（ℐ 支撑不足），并返回 `[DEAD_ZERO_REJECT]: 无据不记。` |
| US2 | 系统（记忆管理者） | 当先后输入"心主神明"和"脑主神明"时，系统应标记 `[MUS_ACTIVE]`，两条均存，检索时双显 |
| US3 | 用户（记忆查询者） | 问"你三个月前记得我怕冷时，你在想什么？"，系统应回答："我记得那时我持有'照顾你健康'的 ψ-锚，正处于脏腑辨证模式（κ=4）。" |
| US4 | 开发者（集成者） | 可以通过 `token_bridge.py --enable-memos` 一键启用 MemOS 融合层，无需修改业务代码 |
| US5 | 系统（遗忘管理者） | 普通记忆随 ℐ 衰减归档；MUS 记忆即使 ℐ 衰减也不删除，保留潜存分支（冬藏） |

---

## 3. 需求池

### P0（核心功能）

| ID | 需求 | 验收标准 |
|----|------|----------|
| R1 | 死零校验写入门控 | 输入低 ℐ 值语句（如"太阳绕地球转"），`write_memory()` 返回 `DEAD_ZERO_REJECT`；输入高 ℐ 值语句，正常写入 |
| R2 | MUS 双存 | 输入一对 Asym≠0 的矛盾语句，`recall_memory()` 返回两条均被激活；而非仅返回最新一条 |
| R3 | ψ-锚附加与回溯 | `write_memory()` 写入时附加 ψ-锚（self_state, kappa_at_write, timestamp）；`recall_memory()` 能在回答中引用 ψ-锚信息 |
| R4 | TOMAS_MemOS_Fusion 类 | 提供 `write_memory(user_input, context)` 和 `recall_memory(query, current_kappa)` 两个公开方法 |
| R5 | 与 token_bridge 集成 | `token_bridge.py` 新增 `--enable-memos` 参数，推理时自动调用融合层 |

### P1（重要功能）

| ID | 需求 | 验收标准 |
|----|------|----------|
| R6 | κ-Gate 激活 | `recall_memory()` 根据 `current_kappa` 值过滤候选记忆，仅激活对应度类的超边 |
| R7 | ℐ-衰减遗忘 | 定期（或每次写入时）对 EML 超边执行 ℐ-衰减；低于 θ_archieve 的超边移入归档区 |
| R8 | CLI 参数完善 | `token_bridge.py` 新增 `--theta-dead`, `--psi-anchor` 等参数 |

### P2（锦上添花）

| ID | 需求 | 验收标准 |
|----|------|----------|
| R9 | MUS 潜存分支 Continuation | 在推理时，MUS 双存记忆能生成"既…也…"式双分支回答 |
| R10 | ψ-锚可视化 | 前端 EMLGraphVisualization 中，ψ-锚以特殊节点（金色）渲染 |

---

## 4. UI 设计稿

**无独立 UI**。融合层为后端逻辑，集成到现有 `token_bridge.py` CLI 和前端 `DistillPanel.tsx` 的推理结果展示中。

推理结果中新增标签：
- `[DEAD_ZERO_REJECT]` → 红色标签
- `[MUS_ACTIVE]` → 紫色双箭头图标
- `ψ-锚: ...` → 金色锚形图标 + 悬浮详情

---

## 5. 待确认问题

1. **MemOS_Interface 实现方式**：文章中的 `MemOS_Interface()` 是抽象接口，我们是否用现有 EML 文件（`.eml` + `.concepts.json`）来模拟 MemOS 的记忆存储？还是新建一个轻量级 MemoryStore 类？
   - **建议**：用 `EMLFileLoader` + SQLite（`tomas.db` 的 `knowledge_triples` 表）模拟 MemOS，不引入外部 MemOS 依赖。

2. **ℐ 值估算方式**：`estimate_I(user_input, context)` 如何实现？
   - **建议**：用现有 `EMLFileLoader` 计算输入与 EML 超图的匹配度，作为 ℐ 值的代理指标。

3. **ψ-锚的数据结构**：ψ-锚是挂在 EML 超边上，还是独立存储？
   - **建议**：作为超边的 `meta` 字段（JSON）存储，格式：`{"psi_anchor": {"self_state": "...", "kappa_at_write": 4, "timestamp": "2026-06-15"}}`

4. **κ-Gate 与现有 κ-Gate 的关系**：`eml_dimred/` 中已有 `kappa_gate` 函数，是直接复用还是新建？
   - **建议**：复用 `eml_dimred/matroid.py` 中的 `kappa_gate()` 函数。

---

## 6. 参考资料

- 章锋. 《从记忆工程到"有我之忆"：TOMAS 对 MemOS 的升维与重构》. 复合体理学, 2026-06-15.
- 王昊奋. 《AI Memory Engineering and MemOS: Building the Operating System for LLM Agents》.
- 现有代码：`tomas_agi/sim/dead_zero_mus.py`, `tomas_agi/sim/eml_dimred/`, `tomas_agi/sim/token_bridge.py`
