# Changelog

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
