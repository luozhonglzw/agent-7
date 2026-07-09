<!-- badges -->
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Next.js-15-000000?logo=next.js&logoColor=white" alt="Next.js">
  <img src="https://img.shields.io/badge/Qdrant-1.12-DC2626?logo=data:image/svg+xml;base64,..." alt="Qdrant">
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License">
</p>

<h1 align="center">企业级知识库 RAG 系统</h1>

<p align="center">
  基于 FastAPI + Next.js + Qdrant 的<strong>生产级检索增强生成（RAG）</strong>系统<br>
  支持多格式文档智能解析、混合检索、RBAC 权限控制与全链路审计
</p>

---

## ✨ 主要特性

| 特性 | 说明 |
|------|------|
| 📄 **智能文档解析** | PDF 自动分类（数字/扫描/混合/复杂布局），支持 PDF、DOCX、Markdown、PPTX、代码等 30+ 格式 |
| 🔍 **混合检索** | Dense（BGE-M3）+ Sparse（BM25）+ RRF 融合 + Reranker 重排，召回率与精度兼顾 |
| 🤖 **流式问答** | 基于 LLM 的 RAG 问答，SSE 流式输出，附带源引用 |
| 🔐 **RBAC 权限** | Casbin 策略引擎，admin / manager / user 三级角色，支持部门级数据隔离 |
| 📋 **审计日志** | 全链路操作追踪，异步写入不阻塞主请求，支持按用户/操作/时间过滤 |
| 🏢 **知识库管理** | 多知识库隔离，支持公开/私有/部门三种可见性 |
| ⚡ **异步处理** | Celery 任务队列，文档解析/分块/Embedding 全链路异步 |
| 🐳 **容器化部署** | Docker Compose 一键启动 8 个服务（API、Worker、DB、Redis、Qdrant…） |

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        接入层 (Nginx)                            │
│                  反向代理 / 负载均衡 / HTTPS                      │
├──────────────────────┬──────────────────────────────────────────┤
│   前端 (Next.js 15)  │          后端 API (FastAPI)               │
│   React 19 + Zustand │          Uvicorn + ASGI                  │
├──────────────────────┴──────────────────────────────────────────┤
│                      鉴权层 (AuthN / AuthZ)                      │
│         JWT (15min/7d) → Casbin RBAC → 审计日志装饰器             │
├─────────────────────────────────────────────────────────────────┤
│                       业务层 (Services)                          │
│    AuthService │ DocumentService │ SearchService │ KBService     │
├─────────────────────────────────────────────────────────────────┤
│                       引擎层 (Engines)                           │
│  PDF分类解析 │ 混合检索(Dense+Sparse+Rerank) │ LLM 流式生成       │
├──────────────────────┬──────────────────────────────────────────┤
│   PostgreSQL 16      │   Redis 7   │   Qdrant v1.12             │
│   用户/文档/知识库    │   缓存/队列  │   向量存储                  │
├──────────────────────┴──────────────────────────────────────────┤
│                    基础设施层 (Docker Compose)                    │
│      Celery Worker │ Celery Beat │ Nginx │ 健康检查              │
└─────────────────────────────────────────────────────────────────┘
```

### 核心数据流

**文档入库流：**
```
上传 → 文件校验 → 保存磁盘 → 创建DB记录 → Celery任务
  → PDF分类(Native/Scanned/Hybrid/Complex)
  → 专用解析器提取文本
  → 重叠分块(1000字/200字重叠)
  → BGE-M3 Embedding
  → Qdrant 向量入库
  → 更新状态 → READY
```

**问答检索流：**
```
用户提问 → Query理解 → Dense检索(BGE-M3) + Sparse检索(BM25)
  → RRF 融合排序 → BGE-Reranker 重排
  → 构建 Prompt (Top-K 上下文)
  → LLM 流式生成 → SSE 推送
  → 附带源引用(文档名/页码/原文)
```

---

## 🚀 快速开始

### 环境要求

- **Docker** >= 24.0
- **Docker Compose** >= 2.20
- **Python** >= 3.11（本地开发）
- **Node.js** >= 20（前端本地开发）

### 一键启动

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/rag-kb-system.git
cd rag-kb-system

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填写以下必填项：
#   POSTGRES_PASSWORD=your_password
#   JWT_SECRET_KEY=$(openssl rand -base64 32)
#   LLM_API_KEY=your_llm_api_key

# 3. 启动所有服务
docker-compose up -d

# 4. 等待服务就绪（约 30 秒）
docker-compose ps

# 5. 访问
#    前端：  http://localhost:3000
#    API：   http://localhost:8000
#    Swagger: http://localhost:8000/docs  (debug 模式)
```

### 本地开发

```bash
# 后端
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
uvicorn app.main:app --reload

# 前端
cd frontend
npm install
npm run dev
```

---

## 📁 项目结构

```
rag-kb-system/
├── docker-compose.yml          # 开发环境（8 个服务）
├── docker-compose.prod.yml     # 生产环境
├── .env.example                # 环境变量模板
├── Makefile                    # 常用命令
│
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── main.py             # 应用入口 + 生命周期管理
│   │   ├── config.py           # Pydantic Settings（10 个配置类）
│   │   ├── database.py         # AsyncSession + 连接池
│   │   ├── exceptions.py       # 统一异常体系（错误码 1000-5999）
│   │   ├── celery_app.py       # Celery 配置 + 信号处理
│   │   │
│   │   ├── api/
│   │   │   ├── dependencies.py # JWT 认证 + require_role + require_permission
│   │   │   └── v1/
│   │   │       ├── auth.py     # 注册/登录/刷新/Profile
│   │   │       ├── documents.py# 文档上传/列表/删除/替换
│   │   │       ├── knowledge_bases.py # 知识库 CRUD + 文档关联
│   │   │       ├── search.py   # 混合检索 + RAG 问答
│   │   │       ├── admin.py    # 用户管理/系统统计
│   │   │       └── audit.py    # 审计日志查询
│   │   │
│   │   ├── core/
│   │   │   ├── middleware.py   # CORS/请求ID/日志/错误处理
│   │   │   ├── security/
│   │   │   │   ├── jwt.py      # JWT 签发/验证
│   │   │   │   ├── password.py # bcrypt 哈希
│   │   │   │   ├── rbac.py     # Casbin 引擎 + 策略管理
│   │   │   │   └── audit.py    # @audit_log 装饰器
│   │   │   ├── parsers/
│   │   │   │   ├── pdf_classifier.py  # PDF 四分类器
│   │   │   │   ├── parser_factory.py  # 分类→解析器路由
│   │   │   │   └── pdf/              # 四种专用解析器
│   │   │   │       ├── native_parser.py
│   │   │   │       ├── scanned_parser.py
│   │   │   │       ├── hybrid_parser.py
│   │   │   │       └── complex_parser.py
│   │   │   ├── chunking/       # 文本分块
│   │   │   ├── retrieval/      # 检索引擎
│   │   │   └── llm/            # LLM 客户端
│   │   │
│   │   ├── models/
│   │   │   ├── base.py         # UUID PK + 时间戳 + 软删除
│   │   │   ├── user.py         # 用户 + 会话
│   │   │   ├── document.py     # 文档 + 分块
│   │   │   ├── knowledge_base.py # 知识库 + 文档关联
│   │   │   ├── audit.py        # 审计日志（追加写入）
│   │   │   └── casbin_rule.py  # Casbin 策略存储
│   │   │
│   │   ├── schemas/            # Pydantic 请求/响应模型
│   │   ├── services/           # 业务逻辑层
│   │   └── tasks/              # Celery 异步任务
│   │
│   ├── alembic/                # 数据库迁移
│   ├── tests/                  # pytest 测试
│   └── requirements.txt
│
└── frontend/                   # Next.js 前端
    ├── app/
    │   ├── layout.tsx          # 全局布局
    │   └── page.tsx            # 首页
    ├── lib/
    │   └── api.ts              # 类型安全 API 客户端 + Token 自动刷新
    ├── types/
    │   └── index.ts            # TypeScript 类型（镜像后端 Schema）
    └── package.json
```

---

## 📚 API 文档

启动后访问 **Swagger UI**：[http://localhost:8000/docs](http://localhost:8000/docs)（仅 debug 模式）

### 主要接口

| 模块 | 端点 | 说明 |
|------|------|------|
| **认证** | `POST /api/v1/auth/register` | 用户注册（密码强度校验） |
| | `POST /api/v1/auth/login` | 登录（返回 JWT 15min + Refresh 7d） |
| | `POST /api/v1/auth/refresh` | 刷新 Token |
| | `GET /api/v1/auth/me` | 获取当前用户信息 |
| **文档** | `POST /api/v1/documents/upload` | 上传文档（multipart/form-data） |
| | `GET /api/v1/documents` | 文档列表（分页 + 状态过滤） |
| | `GET /api/v1/documents/{id}` | 文档详情 |
| | `DELETE /api/v1/documents/{id}` | 软删除文档 |
| | `PUT /api/v1/documents/{id}` | 更新文档元数据 |
| | `POST /api/v1/documents/{id}/replace` | 替换文件并重新处理 |
| **知识库** | `POST /api/v1/knowledge-bases` | 创建知识库 |
| | `GET /api/v1/knowledge-bases` | 知识库列表 |
| | `PUT /api/v1/knowledge-bases/{id}` | 更新知识库 |
| | `DELETE /api/v1/knowledge-bases/{id}` | 删除知识库 |
| | `POST /api/v1/knowledge-bases/{id}/documents` | 关联文档 |
| **检索** | `POST /api/v1/search` | 混合检索 |
| | `POST /api/v1/search/ask` | RAG 问答（SSE 流式） |
| **管理** | `GET /api/v1/admin/users` | 用户列表（admin） |
| | `GET /api/v1/admin/stats` | 系统统计 |
| **审计** | `GET /api/v1/audit/logs` | 审计日志（admin） |

---

## 🔧 核心功能详解

### 智能文档解析

系统对 PDF 文档进行**自动分类**，选择最优解析策略：

```
PDF → PDFClassifier（< 100ms）
  ├── NATIVE  (100% 数字文本) → NativePDFParser (PyMuPDF 直接提取)
  ├── SCANNED (100% 扫描图片) → ScannedPDFParser (PaddleOCR 300dpi)
  ├── HYBRID  (混合页面)      → HybridPDFParser (逐页路由)
  └── COMPLEX (复杂布局)      → ComplexPDFParser (Docling 深度分析)
```

解析失败自动降级：`COMPLEX → HYBRID → NATIVE → Unstructured`

### 混合检索

```python
# Dense 检索（语义相似度）
dense_results = qdrant.search(query_embedding, limit=20)

# Sparse 检索（关键词匹配）
sparse_results = bm25.search(query_tokens, limit=20)

# RRF 融合
fused = reciprocal_rank_fusion(dense_results, sparse_results)

# Reranker 重排
final = bge_reranker.rerank(query, fused[:10], top_k=5)
```

### RBAC 权限矩阵

| 操作 | admin | manager | user |
|------|:-----:|:-------:|:----:|
| 文档 CRUD | ✅ | ✅ | ✅ |
| 文档删除 | ✅ | ✅ | 仅自己的 |
| 知识库管理 | ✅ | ✅ | 仅自己的 |
| 用户管理 | ✅ | ❌ | ❌ |
| 审计日志 | ✅ | ❌ | ❌ |
| 系统配置 | ✅ | ❌ | ❌ |

---

## 🧪 测试

```bash
# 运行全部测试
cd backend
pytest tests/ -v

# 运行特定模块
pytest tests/test_core/ -v          # 核心模块
pytest tests/test_services/ -v      # 服务层
pytest tests/test_api/ -v           # API 端点

# 带覆盖率
pytest tests/ -v --cov=app --cov-report=term-missing

# 运行单个测试文件
pytest tests/test_core/test_parsers.py -v
```

---

## 🛠️ 开发规范

- **Commit Message** 遵循 [Conventional Commits](https://www.conventionalcommits.org/)
  ```
  feat(auth): 添加密码强度校验
  fix(parser): 修复 PDF 分类器对空白页的误判
  docs(readme): 更新快速开始指南
  ```
- 所有代码必须有**类型注解**和 **docstring**
- 单元测试覆盖率 **>= 70%**
- 使用 `ruff` 格式化 + `mypy` 类型检查

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

<p align="center">
  <sub>Built with ❤️ by the RAG-KB Team</sub>
</p>
