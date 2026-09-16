# 智能会议室预约助手

基于 DeepSeek 大模型 + 智能体框架 + 知识检索的智能会议室预约助手。用户通过自然语言即可完成会议室查询、预约、取消、修改和规则问答。

## 核心技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 大语言模型 | DeepSeek（deepseek-chat） | 兼容主流接口，支持函数调用 |
| 智能体框架 | LangChain 0.3 | 工具调用、记忆管理、智能体编排 |
| 知识检索 | Chroma 向量库 | 本地向量检索，无需额外服务 |
| 数据库 | SQLite + SQLAlchemy | 会议室和预约记录存储 |
| 前端界面 | Streamlit | 对话式网页界面 |

## 快速开始

### 1. 安装依赖

```bash
cd meeting-agent
pip install -r requirements.txt
```

### 2. 配置密钥

```bash
# 复制环境变量模板
copy .env.example .env   # Windows 系统
cp .env.example .env     # macOS/Linux 系统

# 编辑 .env 文件，填入你的 DeepSeek 密钥
```

> 获取密钥：访问 https://platform.deepseek.com/ 注册后在「密钥管理」页面创建。

### 3. 初始化数据库

```bash
python data/init_db.py
```

### 4. 启动应用

```bash
python -m streamlit run app.py
```

浏览器自动打开 `http://localhost:8501`，即可与助手对话。

## 使用示例

| 场景 | 输入示例 |
|------|----------|
| 预约会议室 | 帮我约明天下午2点到4点的10人会议室 |
| 查询可用 | 后天上午有哪些能容纳20人的会议室？ |
| 规则问答 | 取消预约要提前多久？ |
| 查看预约 | 我有哪些预约？ |
| 取消预约 | 取消预约号 #000001 |
| 修改预约 | 把预约#000003改到下午3点 |

## 项目结构

```
meeting-agent/
├── .env.example              # 密钥配置模板
├── .gitignore
├── requirements.txt         # 依赖清单
├── app.py                    # 网页前端入口
├── README.md
├── core/                     # 核心逻辑
│   ├── __init__.py
│   ├── config.py             # 配置（密钥、模型、路径）
│   ├── database.py           # 数据模型
│   ├── tools.py              # 工具定义（查询/预约/取消/列表/修改）
│   ├── rag.py                # 知识检索链
│   ├── prompts.py            # 系统提示词模板
│   └── agent.py              # 智能体主逻辑
├── data/                     # 数据
│   ├── init_db.py            # 数据库初始化 + 测试数据
│   ├── meeting.db            # 数据库文件（运行后生成）
│   └── rules/                # 规章制度文档（知识库数据源）
│       ├── room_usage_policy.txt   # 会议室使用管理办法
│       ├── booking_rules.txt       # 预约常见问题
│       └── equipment_guide.txt     # 设备配置指南
├── chroma_db/                # 向量库（运行后生成）
└── tests/
    └── test_agent.py         # 测试用例
```

## 智能体架构

```
用户输入 → 网页界面
              ↓
      智能体执行器（编排层）
       ↙      |       ↘
  工具（5个）  记忆    知识检索
  ↙  ↘  ↘  ↘            ↓
 查询 预约 取消 ...    向量库
  ↓                    ↑
 数据库            规章制度文档
```

智能体采用「推理+行动」模式：
1. 大模型解析用户意图
2. 选择调用合适的工具（操作类 / 问答类）
3. 执行工具，获取结果
4. 根据结果生成自然语言回复
5. 多轮对话通过记忆模块保持上下文

## 运行测试

```bash
python tests/test_agent.py
```

## 常见问题

**问：首次运行很慢？**
答：首次运行时会下载向量编码模型（约80MB），下载后会缓存到本地，后续启动很快。

**问：报错「未检测到大模型密钥」？**
答：确保 .env 文件在项目根目录，且已填入正确的密钥。

**问：如何重置数据库？**
答：删除 `data/meeting.db` 文件后重新运行 `python data/init_db.py`。

**问：如何重置向量库？**
答：删除 `chroma_db/` 目录，下次运行时会自动重建。