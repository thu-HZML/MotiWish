# MotiWish Backend

后端采用 Django + Django REST Framework + PostgreSQL，按单体架构划分为多个业务 app。

## 目录

```text
backend/
  apps/
  config/
  manage.py
  requirements.txt
  docker-compose.yml
  .env.example
```

## 技术栈

- Web 框架：Django 4.2
- API 框架：Django REST Framework
- 鉴权：JWT（SimpleJWT）
- 数据库：PostgreSQL
- 接口文档：drf-spectacular / OpenAPI 3
- AI 框架：LangChain + LangGraph
- AI Provider 接入：OpenAI-compatible / Mock Provider
- 图片处理：Pillow

## AI 模块说明

当前 `apps/ai/` 已经搭建了一个面向长期演进的 LangGraph 风格骨架，主要用于后续接入 Agent 智能体能力。

当前结构包括：

```text
apps/ai/
  agents/        # workflow 注册中心
  graphs/        # LangGraph 风格图工作流
  prompts/       # Prompt 模板
  providers/     # 大模型提供方封装
  tools/         # Agent 可调用的上下文工具
  services.py    # Django 服务入口
  models.py      # AI 报告任务与 Agent 运行记录
```

目前已内置：

- `mock_goal_planner`：用于长期目标拆解的 mock workflow
- `mock provider`：用于本地无外部模型依赖时验证链路
- `openai-compatible provider`：为后续接入兼容 OpenAI 接口的模型服务做准备

## 本地开发

```bash
docker compose up -d db
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## 默认开发地址

- API 文档：`http://127.0.0.1:8000/api/docs/`
- OpenAPI Schema：`http://127.0.0.1:8000/api/schema/`
- Admin：`http://127.0.0.1:8000/admin/`

## 导入 Apifox

启动后端后，可以直接用 `curl` 拉取 OpenAPI 文件，再导入 Apifox：

```bash
curl http://127.0.0.1:8000/api/schema/ -o motiwish-openapi.yaml
```

JWT 鉴权请求头格式：

```http
Authorization: Bearer <access_token>
```

## AI 环境变量

本地开发默认读取 `backend/.env`，模板见 `backend/.env.example`。

和 AI 相关的主要变量包括：

```env
AI_PROVIDER=mock
AI_MODEL=mock-gpt
AI_API_KEY=
AI_BASE_URL=
AI_TEMPERATURE=0.2
AI_TIMEOUT=60
AI_MAX_RETRIES=2
```

说明：

- `AI_PROVIDER=mock` 适合本地验证 Agent 链路
- `AI_PROVIDER=openai-compatible` 适合接入兼容 OpenAI 接口的模型服务

## AI 测试

如果你想先验证当前 mock Agent 链路，可以运行：

```bash
python manage.py test apps.ai -v 2
```

更推荐补充并运行最小 smoke test，覆盖这条链路：

1. 创建用户
2. 创建 `AIAgentRun`
3. 执行 `mock_goal_planner`
4. 检查状态、trace_id 和 result_payload
