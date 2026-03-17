# RAG知识库使用指南

## 概述

RAG (Retrieval-Augmented Generation) 知识库用于在设计评估时自动引用相关规范条文。

## 功能

- **语义搜索**：根据语义相似度查找规范内容，而非简单的关键词匹配
- **规范引用**：在评估报告中自动添加规范引用（如"参考: GB 50010-2010"）
- **构造检查增强**：为构造要求检查提供规范依据

## 快速开始

### 1. 安装依赖

```bash
pip install chromadb
```

### 2. 初始化知识库

```bash
# 首次初始化（如果已有数据会跳过）
python scripts/initialize_rag.py

# 强制重新加载
python scripts/initialize_rag.py --force
```

### 3. 测试功能

```bash
python scripts/test_rag.py
```

## 添加新规范文档

### 1. 准备文档

将规范文档转换为Markdown格式，放入 `knowledge_base/documents/` 目录：

```
knowledge_base/
└── documents/
    ├── GB50010-2010_concrete_standard.md
    ├── GB50017-2017_steel_standard.md
    └── your_new_standard.md  # 新增文档
```

### 2. 文档格式建议

```markdown
# GB XXXXX-YYYY 规范名称

## 第X章 章节名称

### X.X.X 条文编号

条文内容...

**关键参数:**
- 参数1: 值
- 参数2: 值
```

### 3. 重新加载知识库

```bash
python scripts/initialize_rag.py --force
```

## 向量化原理

### 什么是向量化

将文本转换为数学向量（一串数字），使计算机能够理解文本的语义含义。

**示例**：

```
原始文本: "简支梁的挠度不应超过跨度的1/400"
向量化后: [0.23, -0.45, 0.67, 0.12, ...]  # 1536维向量

查询文本: "梁的变形限制是多少"
向量化后: [0.25, -0.43, 0.65, 0.10, ...]  # 语义相近，向量也相近

结果: 找到最相似的文本
```

### 工作流程

```
1. 文档分块
   ↓
2. 文本向量化 (OpenAI Embedding API)
   ↓
3. 存储到ChromaDB
   ↓
4. 查询时：
   - 查询文本向量化
   - 计算向量距离
   - 返回最相似的文本块
```

## 在评估中使用

RAG功能已集成到评估器中，会自动工作：

```python
# 评估器自动查询规范
issue = {
    'type': 'height_span_ratio',
    'message': '梁高跨比不满足要求'
}

# RAG增强后
enhanced_message = "梁高跨比不满足要求 (参考: GB 50010-2010 第9.2.1条)"
```

## 当前状态

- ✅ ChromaDB已安装
- ✅ 向量数据库已初始化
- ✅ 已加载2个规范文档（混凝土规范、钢结构规范）
- ✅ 共7个文本块
- ✅ 语义搜索功能正常

## 故障排除

### 问题1：ChromaDB not available

**原因**：chromadb未安装

**解决**：
```bash
pip install chromadb
```

### 问题2：知识库为空

**原因**：未初始化向量数据库

**解决**：
```bash
python scripts/initialize_rag.py
```

### 问题3：查询无结果

**原因**：
- 知识库中没有相关内容
- 查询词与文档内容差异太大

**解决**：
- 添加更多规范文档
- 调整查询关键词
- 检查文档内容是否正确

### 问题4：protobuf版本冲突

**警告信息**：
```
ansys-api-mapdl requires protobuf<5,>=3.19, but you have protobuf 6.33.5
```

**影响**：不影响RAG功能，但可能影响Ansys功能

**解决**（如果Ansys出现问题）：
```bash
pip install "protobuf>=3.19,<5"
```

## 技术栈

- **ChromaDB**: 向量数据库
- **OpenAI Embedding API**: 文本向量化（text-embedding-ada-002）
- **LangChain**: RAG框架（可选，当前未使用）

## 性能优化

### 文本分块策略

- 默认块大小：1000字符
- 重叠大小：200字符
- 在段落或句子边界分割

### 查询优化

- 默认返回2-3个最相关结果
- 可通过metadata过滤特定规范
- 支持语义相似度阈值过滤

## 未来扩展

- [ ] 支持更多规范文档（地基规范、抗震规范等）
- [ ] 支持PDF文档自动解析
- [ ] 支持多语言规范（英文、日文等）
- [ ] 支持规范版本管理
- [ ] 支持规范条文关联分析
