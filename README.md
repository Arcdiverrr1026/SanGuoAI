# 三国密策阁：基于 LlamaIndex 的知识库问答助手

这是一个基于 **LlamaIndex** 和 **FastAPI** 架构开发的三国演义知识库问答系统，配有精心设计的**毛玻璃战场风** Web 交互界面。
系统支持自定义大语言模型（LLM）与外挂嵌入模型（Embedding），具备多模型动态加载、多参数调整、文档在线上传更新及对话语义匹配收藏等核心功能。

---

## 📂 项目结构说明

```text
/Users/lucent/sanguoai/
├── config.yaml          # 默认配置文件（大模型/嵌入模型、分块参数、检索 Top-K 等）
├── config.py            # 配置管理模块（ConfigManager，支持前端动态参数修改与自动持久化）
├── app.py               # FastAPI 后端服务（提供问答、配置、上传和收藏夹的 REST APIs）
├── README.md            # 项目说明文档（本文件）
├── pyproject.toml       # 项目依赖定义文件（通过 uv 管理包）
├── uv.lock              # uv 锁文件
├── core/
│   ├── __init__.py
│   ├── models.py        # 自定义 LLM (CustomLLM) 与 嵌入模型 (CustomEmbeddings) 适配模块
│   └── engine.py        # LlamaIndex 调度中心（文档加载、SentenceSplitter 文本切割与向量持久化）
├── data/
│   ├── sanguo.txt       # 初始整理的三国演义核心知识点文本
│   └── favorites.json   # 收藏夹数据库（保存已收藏的问答对及问题向量，用于语义预检索）
├── vector_store/        # 向量数据库存储根目录（根据当前激活的“模型_ChunkSize_Overlap”细分目录存储）
└── static/
    ├── index.html       # Web 前端交互页面
    ├── index.css        # 前端界面样式表（战地黄沙与烈火旌旗暗色主题，自适应战场背景）
    ├── index.js         # 前端 JavaScript 逻辑（负责上传、收藏、配置同步与聊天通信）
    └── bg.png           # 战场背景壁纸
```

---

## 🛠️ 依赖管理与环境准备

项目使用 **`uv`** 管理虚拟环境与 Python 包依赖：

```bash
# 进入项目目录
cd /Users/lucent/sanguoai

# 若当前终端已激活了其他路径的虚拟环境，请先退出
deactivate

# 使用 uv 同步依赖包并自动还原虚拟环境
uv sync
```

---

## 🚀 启动与运行

在 `/Users/lucent/sanguoai` 根目录下，直接使用 `uv run` 启动后端服务器：

### 推荐启动命令：
```bash
# 启动 FastAPI 后端服务（支持热重载）
uv run python app.py
```

或者使用指定参数的 Uvicorn 启动命令：
```bash
uv run python -m uvicorn app:app --reload --port 8088
```

服务启动后，在浏览器访问：
👉 **[http://localhost:8088](http://localhost:8088)**

---

## 💻 PyCharm 运行配置说明

若在 PyCharm 中运行，由于项目路径变更，您需要配置有效的 Python SDK（解释器）：
1. 在 PyCharm 中打开 **Settings (Cmd + ,)** -> **Project: sanguoai** -> **Python Interpreter**。
2. 点击 **Add Interpreter** -> **Add Local Interpreter...**，选择 **Existing** 虚拟环境。
3. 将路径指向项目根目录下的虚拟环境：
   `/Users/lucent/sanguoai/.venv/bin/python`
4. 保存配置后，直接点击右上角运行 `app` 即可。

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
- **语义直达**：当您提问时，系统会率先通过 Cosine 相似度将提问与收藏库的问题进行语义对比。若**匹配度 > 82%**，则绕过 RAG 检索与大模型计算，在 **0.05 秒**内直接从收藏库召回答案，并在聊天界面上提示 `【✨ 已直接从收藏秘策中召回 (匹配度: XX.X%)
`，为您大幅节省 Token。
