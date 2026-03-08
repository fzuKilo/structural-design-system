# RAG知识库集成指南

## 概述

本项目集成了RAG (Retrieval-Augmented Generation) 知识库系统,用于查询结构设计规范和标准。

## 功能特性

- **向量化检索**: 使用ChromaDB进行语义搜索
- **多格式支持**: 支持PDF、TXT、MD格式的规范文档
- **标准引用**: 自动提取规范编号并生成引用
- **构造评分增强**: 为构造检查提供规范依据

## 目录结构

```
structural-design-system/
├── structural_app/
│   └── knowledge_base/
│       ├── __init__.py
│       ├── document_loader.py      # 文档加载器
│       ├── rag_engine.py           # RAG引擎核心
│       └── rag_enhanced_mixin.py   # 评估器增强混入类
├── knowledge_base/
│   ├── documents/                  # 规范文档存放目录
│   │   ├── GB50010-2010_concrete_standard.md
│   │   └── GB50017-2017_steel_standard.md
│   └── chroma_db/                  # 向量数据库存储目录
└── scripts/
    └── initialize_knowledge_base.py  # 初始化脚本
```

## 快速开始

### 1. 安装依赖

```bash
pip install chromadb langchain PyPDF2
```

### 2. 初始化知识库

```bash
python scripts/initialize_knowledge_base.py
```

这将:
- 加载 `knowledge_base/documents/` 目录下的所有文档
- 将文档分块并向量化
- 存储到ChromaDB向量数据库
- 运行测试查询验证功能

### 3. 添加新的规范文档

将规范文档放入 `knowledge_base/documents/` 目录:

```bash
# 支持的格式
knowledge_base/documents/
├── GB50010-2010_concrete_standard.md    # Markdown
├── GB50017-2017_steel_standard.md       # Markdown
├── JGJ3-2010_technical_specification.txt # 纯文本
└── GB50009-2012_load_code.pdf           # PDF (需要PyPDF2)
```

然后重新运行初始化脚本。

## 使用方法

### 方法1: 直接使用RAG引擎

```python
from structural_app.knowledge_base import RAGEngine

# 初始化引擎
rag = RAGEngine()

# 查询规范
results = rag.query("beam height span ratio requirements", n_results=3)

for result in results:
    print(f"Source: {result['metadata']['filename']}")
    print(f"Content: {result['content']}")
```

### 方法2: 在评估器中使用 (推荐)

```python
from structural_app.tool.evaluators.base_evaluator import DesignEvaluator
from structural_app.tool.evaluators.rag_enhanced_mixin import RAGEnhancedEvaluatorMixin

class BeamEvaluator(DesignEvaluator, RAGEnhancedEvaluatorMixin):
    def __init__(self):
        DesignEvaluator.__init__(self)
        RAGEnhancedEvaluatorMixin.__init__(self)

    def _check_structure_specific_construction(self, design, results):
        issues = []

        # ... 构造检查逻辑 ...

        # 为每个问题添加规范引用
        enhanced_issues = []
        for issue in issues:
            enhanced_issue = self.enhance_construction_issue_with_citation(
                issue=issue,
                structure_type='beam'
            )
            enhanced_issues.append(enhanced_issue)

        return enhanced_issues
```

## API参考

### RAGEngine

#### `__init__(collection_name, persist_directory, embedding_model)`
初始化RAG引擎

**参数:**
- `collection_name`: ChromaDB集合名称 (默认: "structural_standards")
- `persist_directory`: 数据库持久化目录 (默认: "knowledge_base/chroma_db")
- `embedding_model`: 嵌入模型名称 (默认: "text-embedding-ada-002")

#### `add_documents(documents)`
添加文档到向量数据库

**参数:**
- `documents`: 文档列表,每个文档包含 'content' 和 'metadata'

**返回:** `bool` - 成功返回True

#### `query(query_text, n_results, filter_metadata)`
查询知识库

**参数:**
- `query_text`: 查询字符串
- `n_results`: 返回结果数量 (默认: 3)
- `filter_metadata`: 元数据过滤条件 (可选)

**返回:** `List[Dict]` - 结果列表

#### `query_standard(structure_type, check_type, n_results)`
查询特定结构类型的规范要求

**参数:**
- `structure_type`: 结构类型 (如 'beam', 'truss')
- `check_type`: 检查类型 (如 'height_span_ratio')
- `n_results`: 返回结果数量 (默认: 2)

**返回:** `List[Dict]` - 规范条款列表

### RAGEnhancedEvaluatorMixin

#### `query_standard_citation(structure_type, check_type, n_results)`
查询规范引用

**返回:** `str` - 规范引用字符串 (如 "参考: GB 50010-2010")

#### `query_standard_requirement(structure_type, check_type, n_results)`
查询详细规范要求

**返回:** `List[Dict]` - 规范要求列表

#### `enhance_construction_issue_with_citation(issue, structure_type)`
为构造问题添加规范引用

**参数:**
- `issue`: 构造问题字典
- `structure_type`: 结构类型

**返回:** `Dict` - 增强后的问题字典 (包含citation字段)

## 文档格式要求

### Markdown格式 (推荐)

```markdown
# GB 50010-2010 混凝土结构设计规范

## 第4章 结构设计基本规定

### 4.2 挠度限值

4.2.1 受弯构件的挠度限值应符合下列规定:

| 构件类型 | 挠度限值 |
|---------|---------|
| 简支梁 | L/250 |
| 悬臂梁 | L/200 |
```

### 纯文本格式

```
GB 50010-2010 混凝土结构设计规范

第4章 结构设计基本规定

4.2 挠度限值

4.2.1 受弯构件的挠度限值应符合下列规定:
- 简支梁: L/250
- 悬臂梁: L/200
```

### 文件命名规范

建议使用以下命名格式:
```
{标准编号}_{简短描述}.{扩展名}

示例:
GB50010-2010_concrete_standard.md
GB50017-2017_steel_standard.md
JGJ3-2010_technical_specification.txt
```

## 测试

### 测试知识库初始化

```bash
python scripts/initialize_knowledge_base.py
```

### 测试RAG混入类

```bash
python tests/test_rag_mixin.py
```

## 性能优化

### 1. 文档分块策略

当前使用简单的段落分块策略,可以根据需要调整:

```python
# 在 rag_engine.py 中
def _split_text(self, text, chunk_size=1000, overlap=200):
    # 调整 chunk_size 和 overlap 参数
    pass
```

### 2. 向量数据库优化

ChromaDB会自动持久化数据,无需每次重新加载文档。

清空数据库:
```python
rag = RAGEngine()
rag.clear()  # 清空所有文档
```

### 3. 查询优化

使用元数据过滤提高查询精度:

```python
results = rag.query(
    "beam requirements",
    n_results=5,
    filter_metadata={'type': 'md', 'filename': 'GB50010*'}
)
```

## 故障排除

### 问题1: ChromaDB初始化失败

**错误信息:** `ModuleNotFoundError: No module named 'chromadb'`

**解决方案:**
```bash
pip install chromadb
```

### 问题2: PDF文档无法加载

**错误信息:** `PDF parsing libraries not available`

**解决方案:**
```bash
pip install PyPDF2
# 或
pip install pdfplumber
```

### 问题3: 查询结果为空

**可能原因:**
1. 知识库未初始化
2. 文档目录为空
3. 查询关键词不匹配

**解决方案:**
1. 运行 `python scripts/initialize_knowledge_base.py`
2. 检查 `knowledge_base/documents/` 目录
3. 调整查询关键词或增加 `n_results`

## 未来改进

- [ ] 支持更多文档格式 (DOCX, HTML)
- [ ] 实现文档更新和版本管理
- [ ] 添加规范条文的结构化解析
- [ ] 集成到DesignAgent进行智能设计
- [ ] 支持多语言规范 (中英文)
- [ ] 实现规范条文的自动摘要

## 相关文档

- [评分系统设计文档](../docs/evaluation_system.md)
- [如何添加新结构类型](../docs/how_to_add_new_structure_type.md)
- [开发计划](../docs/structure_expansion_plan.md)

---

**版本:** v1.0.0
**更新日期:** 2026-03-06
**维护者:** OpenManus Structure Design Team
