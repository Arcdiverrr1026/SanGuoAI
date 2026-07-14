# 三国密策阁：基于 LlamaIndex 的知识库问答助手

这是一个基于 **LlamaIndex** 和 **FastAPI** 架构开发的三国演义知识库问答系统，配有精心设计的**毛玻璃战场风** Web 交互界面。
系统支持自定义大语言模型（LLM）与外挂嵌入模型（Embedding），具备多模型动态加载、多参数调整、文档在线上传更新及对话语义匹配收藏等核心功能。

---

## 📂 项目结构说明

```text
final/
├── config.yaml          # 默认配置文件（大模型/嵌入模型、分块参数、检索 Top-K 等）
├── config.py            # 配置管理模块（ConfigManager，支持前端动态参数修改与自动持久化）
├── app.py               # FastAPI 后端服务（提供问答、配置、上传和收藏夹的 REST APIs）
├── README.md            # 项目说明文档（本文件）
├── core/
│   ├── __init__.py
│   ├── models.py        # 自定义 LLM (CustomLLM) 与 嵌入模型 (CustomEmbeddings) 适配模块
│   └── engine.py        # LlamaIndex 调度中心（文档加载、SentenceSplitter 文本切割与向量持久化）
├── data/
│   ├── sanguo.txt       # 初始整理的三国演义核心知识点文本
│   └── favorites.json   # 收藏夹数据库（保存已收藏的问答对及问题向量，用于语义预检索）
├── vector_store/        # 向量数据库存储根目录（依当前激活的“模型_ChunkSize_Overlap”细分目录存储）
└── static/
    ├── index.html       # Web 前端交互页面
    ├── index.css        # 前端界面样式表（战地黄沙与烈火旌旗暗色主题，带有自适应战场背景）
    ├── index.js         # 前端 JavaScript 逻辑（负责上传、收藏、配置同步与聊天通信）
    └── bg.png           #  battlefield 战地背景壁纸
```

---

## 🛠️ 环境准备与依赖安装

项目运行在 Python 3.12 虚拟环境中。需要确保已安装以下依赖包：

```bash
# 激活您的虚拟环境（若未激活）
source .venv/bin/box/activate  # 或对应您系统的激活脚本

# 安装必要依赖
pip install fastapi uvicorn python-multipart llama-index openai pyyaml numpy
```

---

## 🚀 启动与运行

在 `/Users/lucent/AIGC_project` 根目录下，通过设置 `PYTHONPATH` 环境变量启动后端服务器：

```bash
# 启动 FastAPI 后端服务
PYTHONPATH=. .venv/bin/python final/app.py
```

服务启动后，在浏览器访问：
👉 **[http://localhost:8088](http://localhost:8088)**

---

## 🌟 核心功能特性

### 1. 外挂嵌入模型与自定义 LLM 适配
在前端左侧表单中，您可以输入个人的 API 密钥（API Key）、接口地址（Base URL）及具体模型名称：
- **大模型 (LLM)**：默认配置为智谱 `glm-4`（可动态修改为 `gpt-4o`、`deepseek-chat` 等标准 OpenAI 兼容接口）。
- **嵌入模型 (Embedding)**：默认配置为智谱 `embedding-3`（同样支持更换为 `text-embedding-3-small` 等外部向量接口）。

### 2. 密策阁状态监控与 TXT 文献上传
- **监控看板**：实时呈现当前核心文献库列表及其文件大小，并显示当前向量库中已加载的**总分片条数**和向量存储的路径。
- **在线上传**：点击侧边栏的 **“📂 上传新文献 (.txt)”** 即可上传本地文本，系统接收后会自动保存并在后台**重构整个向量索引**，新文献的内容会立即加入检索。

### 3. 妙计收藏与语义预匹配极速召回
- **一键收藏**：对于满意的回答，点击聊天气泡右下角的 **“⭐ 收藏此策”** 即可收藏，该收藏问答对的文本及问题向量会持久化记录在 `data/favorites.json`。
- **双栏查阅**：右侧抽屉面板提供了 **“📋 召回文献”** 和 **“⭐ 收藏妙计”** 双标签页，支持直接浏览已收录的妙计或进行 **“❌ 移除”**。
- **语义直达**：当您提问时，系统会率先通过 Cosine 相似度将提问与收藏库的问题进行语义对比。若**匹配度 > 82%**，则绕过 RAG 检索与大模型计算，在 **0.05 秒**内直接从收藏库召回答案，并在聊天界面上提示 `【✨ 已直接从收藏秘策中召回 (匹配度: XX.X%)】`，为您大幅节省 Token。
