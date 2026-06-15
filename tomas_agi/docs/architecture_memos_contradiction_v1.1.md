# TOMAS-MemOS 矛盾检测增强 - 增量架构设计

**日期**：2026-06-16  
**基于**：`docs/prd_memos_contradiction_v1.1.md`（增量 PRD）  
**版本**：V1.1（否定词检测）+ V1.2（NLP 主谓宾提取）

---

## 1. 实现方案 + 框架选型

### 1.1 总体架构

```
memos_fusion.py (_is_contradictory)
          ↓
    [增强版矛盾检测器]
          ↓
    ┌─────────────────────────────────────┐
    │  矛盾检测三层架构（按优先级）     │
    ├─────────────────────────────────────┤
    │  Layer 1: 否定词检测（V1.1）    │
    │  Layer 2: NLP 主谓宾提取（V1.2）│
    │  Layer 3: EML 语义相似度（V2.0） │
    └─────────────────────────────────────┘
```

### 1.2 框架选型

| 组件 | 选型 | 理由 |
|------|------|------|
| **NLP 工具（V1.2）** | `jieba` + 规则提取 | 轻量级，无外部依赖，适合中文主谓宾提取 |
| **EML 查询（V2.0）** | `EMLFileLoader`（已有） | 复用现有 `eml_dimred/hyperedge.py` |
| **语义相似度（V2.0）** | 简化版：查询 EML 边的 `asym` 字段 | 直接使用 TOMAS 已有的 asym 机制 |

**为什么不用 LAC？**
- LAC 需要外部依赖（`pip install lac`），增加部署复杂度
- jieba 是 Python 标准中文分词库，轻量且效果好
- 主谓宾提取可以用规则（依存句法）+ jieba 词性标注实现

---

## 2. 文件列表及相对路径（增量）

| 文件 | 变更类型 | 职责 |
|------|-----------|------|
| `tomas_agi/sim/memos_fusion.py` | **修改** | 增强 `_is_contradictory()` 方法，新增三层检测 |
| `tomas_agi/sim/contradiction_detector.py` | **新建** | 独立的矛盾检测器模块（三层架构） |
| `tests/test_contradiction.py` | **新建** | 矛盾检测器测试套件（覆盖 V1.1 + V1.2） |

**总文件数**：3 个（1 个修改 + 2 个新建）

---

## 3. 数据结构和接口（类图）

### 3.1 新增类：`ContradictionDetector`

```python
class ContradictionDetector:
    """
    矛盾检测器（三层架构）
    
    层级：
    - Layer 1: 否定词检测（V1.1）
    - Layer 2: NLP 主谓宾提取（V1.2）
    - Layer 3: EML 语义相似度（V2.0）
    """
    
    def __init__(self, enable_nlp: bool = True, enable_eml: bool = False):
        """
        初始化矛盾检测器
        
        Args:
            enable_nlp: 是否启用 NLP 主谓宾提取（V1.2）
            enable_eml: 是否启用 EML 语义相似度（V2.0）
        """
        self.enable_nlp = enable_nlp
        self.enable_eml = enable_eml
        
        # 否定词词典（Layer 1）
        self.negation_words = ["不", "不是", "不可能", "错误", "不对", "否认", "没有"]
        
        # NLP 工具（Layer 2）
        if enable_nlp:
            self._init_nlp()
        
        # EML 加载器（Layer 3）
        if enable_eml:
            self._init_eml()
    
    def is_contradictory(self, relation1: str, relation2: str) -> bool:
        """
        检测两个关系是否矛盾（主入口）
        
        检测顺序：
        1. Layer 1: 否定词检测（快速）
        2. Layer 2: NLP 主谓宾提取（中等）
        3. Layer 3: EML 语义相似度（慢速）
        
        Args:
            relation1: 第一个关系文本
            relation2: 第二个关系文本
            
        Returns:
            是否矛盾
        """
        # Layer 1: 否定词检测
        if self._layer1_negation(relation1, relation2):
            return True
        
        # Layer 2: NLP 主谓宾提取
        if self.enable_nlp:
            if self._layer2_nlp(relation1, relation2):
                return True
        
        # Layer 3: EML 语义相似度
        if self.enable_eml:
            if self._layer3_eml(relation1, relation2):
                return True
        
        return False
    
    def _layer1_negation(self, relation1: str, relation2: str) -> bool:
        """Layer 1: 否定词检测"""
        # 实现见下文
    
    def _layer2_nlp(self, relation1: str, relation2: str) -> bool:
        """Layer 2: NLP 主谓宾提取"""
        # 实现见下文
    
    def _layer3_eml(self, relation1: str, relation2: str) -> bool:
        """Layer 3: EML 语义相似度"""
        # 实现见下文
    
    def _init_nlp(self):
        """初始化 NLP 工具（jieba + 规则）"""
        # 实现见下文
    
    def _init_eml(self):
        """初始化 EML 加载器"""
        # 实现见下文
```

### 3.2 修改类：`TOMAS_Mem_OS_Fusion`（增量）

```python
class TOMAS_Mem_OS_Fusion:
    def __init__(self, ...):
        # ... 已有代码 ...
        
        # 新增：矛盾检测器
        self.contradiction_detector = ContradictionDetector(
            enable_nlp=True,   # V1.2
            enable_eml=False,  # V2.0（后续启用）
        )
    
    def _is_contradictory(self, relation1: str, relation2: str) -> bool:
        """
        检测两个关系是否矛盾（增强版）
        
        修改点：调用 ContradictionDetector.is_contradictory()
        """
        return self.contradiction_detector.is_contradictory(relation1, relation2)
```

---

## 4. 程序调用流程（时序图）

### 4.1 写入记忆时的矛盾检测流程

```
用户 → TOMAS_Mem_OS_Fusion.write_memory()
                            ↓
                    _is_contradictory(relation, ex.relation)
                            ↓
                ContradictionDetector.is_contradictory()
                            ↓
                    ┌─────────────────────┐
                    │  Layer 1: 否定词？  │
                    │  - 是 → 返回 True  │
                    │  - 否 → 继续       │
                    └─────────────────────┘
                            ↓
                    ┌─────────────────────┐
                    │  Layer 2: NLP？     │
                    │  - 启用 → 主谓宾提取 │
                    │  - 矛盾 → 返回 True │
                    │  - 否 → 继续       │
                    └─────────────────────┘
                            ↓
                    ┌─────────────────────┐
                    │  Layer 3: EML？     │
                    │  - 启用 → 查询 EML  │
                    │  - asym≠0 → True   │
                    │  - 否 → 返回 False │
                    └─────────────────────┘
```

---

## 5. 任务列表（有序、含依赖关系）

### 5.1 V1.1 任务（否定词检测）

| 任务 ID | 任务 | 依赖 | 实现顺序 |
|----------|------|------|----------|
| T1 | 实现 `ContradictionDetector._layer1_negation()` | 无 | 1 |
| T2 | 集成到 `_is_contradictory()` | T1 | 2 |
| T3 | 编写测试用例（`test_contradiction.py::TestLayer1`） | T2 | 3 |

### 5.2 V1.2 任务（NLP 主谓宾提取）

| 任务 ID | 任务 | 依赖 | 实现顺序 |
|----------|------|------|----------|
| T4 | 实现 `_init_nlp()`（jieba + 规则） | 无 | 4 |
| T5 | 实现 `_ extract_spo()` 主谓宾提取 | T4 | 5 |
| T6 | 实现 `_layer2_nlp()` | T5 | 6 |
| T7 | 集成到 `ContradictionDetector.is_contradictory()` | T6 | 7 |
| T8 | 编写测试用例（`test_contradiction.py::TestLayer2`） | T7 | 8 |

### 5.3 V2.0 任务（EML 语义相似度）- 后续迭代

| 任务 ID | 任务 | 依赖 | 实现顺序 |
|----------|------|------|----------|
| T9 | 实现 `_init_eml()`（加载 EML 文件） | 无 | 9 |
| T10 | 实现 `_layer3_eml()`（查询 asym） | T9 | 10 |
| T11 | 集成到 `ContradictionDetector.is_contradictory()` | T10 | 11 |
| T12 | 编写测试用例（`test_contradiction.py::TestLayer3`） | T11 | 12 |

---

## 6. 依赖包列表

| 包名 | 版本 | 用途 | 必需？ |
|------|------|------|--------|
| `jieba` | >=0.42.1 | 中文分词 + 词性标注（Layer 2） | 是（V1.2） |
| `toml` | >=0.10.2 | 配置文件解析（可选） | 否 |

**安装命令**：
```bash
pip install jieba>=0.42.1
```

---

## 7. 共享知识（跨文件约定）

### 7.1 否定词词典格式

```python
NEGATION_WORDS = ["不", "不是", "不可能", "错误", "不对", "否认", "没有"]
```

### 7.2 主谓宾三元组格式

```python
@dataclass
class SPO:
    subject: str    # 主语（如 "心"）
    predicate: str  # 谓语（如 "主"）
    object: str     # 宾语（如 "神明"）
```

### 7.3 EML 查询接口（后续版本）

```python
def query_eml_asym(concept1: str, concept2: str) -> float:
    """
    查询 EML 图中两个概念的 asym 值
    
    Returns:
        asym 值（0 = 无矛盾，≠0 = 矛盾）
    """
    # 实现见 V2.0
```

---

## 8. 待明确事项

1. **NLP 工具性能**：
   - jieba 分词速度：~1000 字/秒（满足需求）
   - 是否需要异步处理？（不需要，矛盾检测是同步操作）

2. **EML 加载策略（V2.0）**：
   - 是否每次查询都加载 EML 文件？（慢）
   - 还是离线预处理概念相似度矩阵？（快，但需要更新机制）
   
   **建议**：V2.0 先实现每次查询加载（简单），V2.1 优化为缓存。

3. **测试覆盖率**：
   - 目标：>=80% 代码覆盖率
   - 重点：Layer 1 + Layer 2 的核心逻辑

---

## 9. 实现顺序（详细）

### 9.1 第一阶段：V1.1（否定词检测）

1. 创建 `contradiction_detector.py` 文件
2. 实现 `ContradictionDetector` 类（骨架）
3. 实现 `_layer1_negation()` 方法
4. 修改 `memos_fusion.py` 中的 `_is_contradictory()` 调用
5. 创建 `test_contradiction.py` 测试文件
6. 编写 `TestLayer1` 测试用例
7. 运行测试，确保通过

### 9.2 第二阶段：V1.2（NLP 主谓宾提取）

1. 安装 `jieba`：`pip install jieba`
2. 实现 `_init_nlp()` 方法（初始化 jieba）
3. 实现 `_extract_spo()` 方法（主谓宾提取）
4. 实现 `_layer2_nlp()` 方法（矛盾判定）
5. 编写 `TestLayer2` 测试用例
6. 运行测试，确保通过

### 9.3 第三阶段：V2.0（EML 语义相似度）- 后续迭代

1. 实现 `_init_eml()` 方法（加载 EML 文件）
2. 实现 `_layer3_eml()` 方法（查询 asym）
3. 编写 `TestLayer3` 测试用例
4. 运行测试，确保通过

---

**增量架构设计结束** — 下一步：工程师基于本文档实现代码。
