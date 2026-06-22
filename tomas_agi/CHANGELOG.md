# Changelog

## [v3.6] - 2026-06-21

### Added
- **v3.6 八模块升级**（基于复合体理学 8 篇微信公众号文章 + MNQ Golden Spirit Ball Simulator + DIKWP Ecosystem）：
  - **ψ-Gate 不确定性门控**：`psi_gate.py`（6 核心锚点、MUS 双存、多世界并行推理、容差衰减控制器）
  - **7+1 语义规范本体**：`eml_kb_ontology.py`（Entity/Attribute/Relation/Event/Temporal/Causal/Constraint + BusinessRule 本体治理、EML-Lite DB 五区架构 L1-L5、Fact→Act 桥接）
  - **解释坩埚**：`interpretation_crucible.py`（波粒二象性、多世界分支、贝叶斯坍缩、MUS 双存解析、解释谱系追踪）
  - **世界模型超边**：`wm_hyperedge.py`（SDF/Affordance/Kinematic 三超边、Ω-Gate Tetrad 联验 π/Φ/Ω/℧）
  - **DIKWP 全桥接**：`dikwp_bridge_full.py`（IntentGuard 意图守卫、MemoryLedger→MUS 映射、DAAP 四层审计、语义安全完备性定理）
  - **太极周期 v2**：`taiji_cycle_v2.py`（EML 脉冲→φ-Gate→T-Processor 闭环、CycleSpinner 自适应调度器、LRU 超边存储）
  - **MNQ 冻结内核**：`mnq_frozen_kernel.py`（五层渐进冻结 L0-L4、八元数非结合度量化、Golden Spirit Ball Fibonacci 投影、κ=7 稳定器）
  - **TOMAS 治疗师扩展**：`tomas_therapist.py` +6 方法（L1 记忆植入、ψ 锚软化、Purpose 内化、MUS 区域创建、治疗摘要、恢复评分）
- 新增 8 个模块文件（7 新建 + 1 修改），+6,432 行代码
- 新增 57 个测试用例（`test_v36_modules.py`，8 测试类），57/57 全部通过
- 全量回归测试 767 项：763 passed + 2 skipped + 2 pre-existing failed（非 v3.6 引入）

### Fixed
- `dikwp_bridge_full.py`：IntentSeverity 从字符串枚举改为整数枚举（SAFE=0, SUSPICIOUS=1, DANGEROUS=2, CRITICAL=3）
- `test_v36_modules.py`：修复 IntentSeverity 作用域问题（setup_method 中添加 `self.IntentSeverity = IntentSeverity`）
- `mnq_frozen_kernel.py`：修复 math 函数别名在常量定义之前的问题

### Changed
- paper.md → v3.6（新增 Appendix L：v3.6 八模块升级）
- README.md：更新特性列表、模块数（79→87）、测试数（729→767）
- Git commit `5381574` 推送至 backend/master

---

## [v2.6] - 2026-06-21

### Added
- **六文章升级**（基于复合体理学 2026-06-20 六篇公众号文章）：
  - HNC 同构映射：`hnc_parser_wrapper.py` + `tomas_nlu_pipeline.py`（NLU 管道 + ℐ 贝叶斯更新）
  - 哥德尔智能体：`goedel_agent_tomas.py`（PG-囚禁 + MUS 双存 + κ-snap 审计链）
  - Aether 因果世界模型：`causal_world_model_tomas.py` + `aether_bridge.py` + `hodge_operator.py` 升级（SCM do-calculus）
  - AgentWeb 分布式时序：`vector_clock.py` + `causal_delivery.py` + `agentweb_runtime.py` + `fediverse_bridge.py`
  - 密码学桥接：`mina_kappa_bridge.py`（Mina SNARK 22KB 证明）+ `celo_bridge.py`（Celo 稳定币支付，RPC 超时降级）
  - EML-EHNN 等变超图：`eml_ehnn.py` + `equivariant_layers.py` + `eml_semzip.py` / `gpct.py` 升级
- 新增 14 个模块文件、修改 8 个已有文件
- 新增 28 个 `/api/v2/*` REST 端点（server.py）
- 前端 V2Panel 组件（6 标签页，覆盖全部 v2 API）
- `/api/knowledge/stats` 端点（全库真实统计，5 分钟内存缓存）

### Fixed
- Celo RPC 超时：超时从 10.0s → 3.0s，快速降级路径
- 前端 DistillPanel 统计卡片：优先使用 `/api/knowledge/stats` 真实数据（替代分页子集）

### Changed
- paper.md → v2.6（新增 Appendix K：六文章升级）
- README.md：更新特性列表，101M+ 三元组 badge

---

## [Unreleased]

### Added
- HyperIndex v2.0: DB-backed k-hop subgraph loading with OrderedDict LRU cache
- UnionFind matroid circuit detection: O(|E|·α(|V|)) complexity
- ChainDB distributed hypergraph: HyperShard + DistributedHyperIndex
- EML v2.0: n-ary hyperedge binary format
- 6 new API endpoints for hypergraph operations
- HypergraphPanel frontend: 5 tabs (overview/k-hop/matroid/distributed/export)
- create_shards.py: HyperShard generation script

### Fixed
- INSERT OR IGNORE pattern in migrate_hypergraph.py (UNIQUE constraint fix)
- matroid-unionfind API: added seeds concept resolution
- export-eml-v2 API: fixed parameter names
- Frontend TypeScript errors in AEGISPanel/TShieldPanel/TProcessorPanel
- tomas_agi package import (added __init__.py)

### Changed
- eml_dimred/__init__.py: v1.0.0 → v2.0.0, 27 exports
- README.md: updated with new features and 101M+ triples badge

---

## [v3.4] - 2026-06-15

### Added
- DIKWP five-layer mapping
- Semantic firewall
- T-Processor/T-Shield panels
- ARC-AGI-3/GAIA/SWE-bench evaluation frameworks

### Fixed
- OwnThink import UNIQUE constraint handling
- Frontend build errors

---

## [v3.0] - 2026-06-01

### Added
- "Translator + Writer" V3 hybrid architecture
- Φ-Gate semantic gating
- EML knowledge distillation
- DeepSeek LLM integration

---

## [v2.0] - 2026-05-01

### Added
- NASGA octonion algebra
- κ-Gate semantic pruning
- Hypergraph data model
- SQLite backend for knowledge storage

---

## [v1.0] - 2026-03-01

### Added
- Initial TOMAS-AGI implementation
- Basic EML knowledge graph
- LSTM-based translator
- Token bridge architecture
