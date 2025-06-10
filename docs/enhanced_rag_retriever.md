# 增强RAG检索器

## 概述

增强RAG检索器(`EnhancedRAGRetriever`)是一个结合了向量相似度召回和倒排索引召回的混合搜索系统。它在原有的代码检索器基础上，增加了基于embedding API的语义搜索能力，实现了更精准的代码检索。

## 核心特性

### 🔍 混合搜索算法
- **向量相似度召回**: 使用embedding API获取文本向量，通过余弦相似度进行语义搜索
- **倒排索引召回**: 基于TF-IDF的关键词匹配搜索
- **智能权重融合**: 可配置的权重系统，动态平衡两种召回方式

### 🚀 多种Embedding支持
- 阿里云百炼DashScope API (text-embedding-v3/v4) 🇨🇳
- OpenAI API (text-embedding-3-small/large)
- OpenRouter API
- Azure OpenAI
- 本地部署的embedding服务
- Hugging Face API

### 📊 高性能存储
- **向量存储**: 基于ChromaDB的高效向量数据库
- **关键词索引**: SQLite + TF-IDF的倒排索引
- **自动索引构建**: 支持增量索引和批量重建

### ⚡ 异步支持
- 完全异步的API设计
- 批量embedding处理
- 并发搜索优化

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                     EnhancedRAGRetriever                    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │ EmbeddingClient │  │   VectorStore   │  │KeywordIndex │  │
│  │   (OpenAI API)  │  │   (ChromaDB)    │  │ (TF-IDF)    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    BaseCodeRetriever                        │
│                  (文件索引 + 基础检索)                         │
└─────────────────────────────────────────────────────────────┘
```

## 使用方法

### 基本初始化

```python
from rag.enhanced_retriever import EnhancedRAGRetriever

# 使用默认配置
retriever = EnhancedRAGRetriever(
    repo_path="/path/to/your/repo",
    db_path="temp/rag_data/enhanced_rag"
)

# 使用自定义embedding配置
embedding_config = {
    "base_url": "https://api.openai.com/v1",
    "model": "text-embedding-3-small", 
    "api_key": "your-api-key"
}

retriever = EnhancedRAGRetriever(
    repo_path="/path/to/your/repo",
    db_path="temp/rag_data/enhanced_rag",
    embedding_config=embedding_config
)
```

### 混合搜索

```python
# 异步混合搜索
results = await retriever.hybrid_search(
    query="向量相似度算法",
    n_results=5,
    vector_weight=0.7,    # 向量权重
    keyword_weight=0.3    # 关键词权重
)

for result in results:
    print(f"文档: {result.document.title}")
    print(f"向量得分: {result.vector_score:.3f}")
    print(f"关键词得分: {result.keyword_score:.3f}")
    print(f"综合得分: {result.combined_score:.3f}")
```

### 标准Retriever接口

```python
# 兼容原有的Retriever接口
documents = retriever.query_relevant_documents("代码检索")
resources = retriever.list_resources("python")
```

## 配置说明

### Embedding配置

支持多种embedding服务配置：

```yaml
# OpenAI
openai:
  base_url: "https://api.openai.com/v1"
  model: "text-embedding-3-small"
  api_key: "${OPENAI_API_KEY}"
  dimensions: 1536

# OpenRouter
openrouter:
  base_url: "https://openrouter.ai/api/v1"
  model: "openai/text-embedding-3-small"
  api_key: "${OPENROUTER_API_KEY}"

# 本地服务
local:
  base_url: "http://localhost:8080/v1"
  model: "sentence-transformers/all-MiniLM-L6-v2"
  api_key: "not-required"
```

### 权重配置

```yaml
search_weights:
  vector_weight: 0.6      # 向量相似度权重
  keyword_weight: 0.4     # 关键词匹配权重
  
  # 根据查询类型调整
  query_type_weights:
    semantic_search:
      vector_weight: 0.8
      keyword_weight: 0.2
    keyword_search:
      vector_weight: 0.3
      keyword_weight: 0.7
```

## 性能优化

### 批量处理
- embedding获取支持批量处理，减少API调用次数
- 索引构建采用批量插入，提升建库速度

### 缓存机制
- embedding结果缓存，避免重复计算
- 查询结果缓存，提升响应速度

### 异步优化
- 全异步API设计，支持高并发
- 向量搜索和关键词搜索并行执行

## 评估指标

系统提供多维度的检索质量评估：

### 召回率指标
- **向量召回准确率**: 基于语义相似度的召回质量
- **关键词召回准确率**: 基于关键词匹配的召回质量  
- **混合召回效果**: 两种方式结合后的整体效果

### 性能指标
- **索引构建时间**: 不同规模代码库的索引构建耗时
- **查询响应时间**: 单次查询的平均响应时间
- **并发处理能力**: 同时处理多个查询的能力

## 最佳实践

### 1. 选择合适的Embedding模型
- **代码搜索**: 推荐使用text-embedding-3-small，平衡效果和成本
- **语义搜索**: 推荐使用text-embedding-3-large，获得更好的语义理解
- **本地部署**: 推荐sentence-transformers模型，无需API调用

### 2. 调整权重配置
- **技术文档**: 提高向量权重(0.7-0.8)，重视语义理解
- **API搜索**: 提高关键词权重(0.6-0.7)，重视精确匹配
- **混合查询**: 使用默认权重(向量0.6，关键词0.4)

### 3. 索引维护
- 定期重建索引以包含新代码
- 监控索引大小和查询性能
- 根据使用模式调整缓存策略

## 故障排除

### 常见问题

1. **Embedding API调用失败**
   - 检查API密钥是否正确
   - 确认网络连接和API服务状态
   - 系统会自动回退到关键词搜索

2. **索引构建缓慢**
   - 减少batch_size降低内存使用
   - 启用并行索引构建
   - 检查磁盘空间是否充足

3. **搜索结果不相关**
   - 调整向量和关键词的权重比例
   - 检查embedding模型是否适合当前场景
   - 考虑重新训练或选择其他模型

### 性能监控

```python
# 获取统计信息
stats = retriever.get_statistics()
print(f"向量存储文档数: {stats['vector_store_count']}")
print(f"索引状态: {stats['enhanced_indexing']}")
print(f"当前权重: 向量{stats['vector_weight']}, 关键词{stats['keyword_weight']}")
```

## 示例代码

完整的使用示例请参考：
- `examples/enhanced_rag_demo.py` - 功能演示
- `tests/test_enhanced_retriever.py` - 单元测试

## 未来改进

- [ ] 支持更多embedding模型
- [ ] 实现增量索引更新
- [ ] 添加查询意图识别
- [ ] 支持多模态检索（代码+文档+图片）
- [ ] 集成更多向量数据库后端 