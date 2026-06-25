# MotiWish 愿动力

MotiWish 是一款 **游戏化时间管理** 应用：把自律行为量化为虚拟货币，再通过抽卡与商城兑换提供惊喜与奖励，形成可持续的正反馈闭环。项目采用 **前后端分离的 Monorepo** 结构，同时承载 Android 客户端与 Django 后端。

> 核心理念：**把自律化作汗水，用运气兑换惊喜。**

---

## 核心业务闭环

```
完成任务 / 日常指标  →  赚取一级货币  →  抽卡  →  获得二级货币  →  商城兑换愿望
         ↑                                                              │
         └──────────── AI 用户画像（任务定价、日常评估、愿望生成）────────┘
```

| 环节 | 说明 |
|------|------|
| **自律产出** | 完成待办、周期任务、专注计时等，获得一级货币（代表努力） |
| **祈愿开箱** | 消耗一级货币抽卡，获得二级货币（代表惊喜） |
| **愿望兑现** | 在商城用二级货币兑换自定义愿望或虚拟道具 |
| **AI 辅助** | 根据用户画像（作息、抗压、奖励偏好等）动态评估任务难度与奖励额度 |

---

## 仓库结构

```text
MotiWish/
├── android/          # Android 客户端（Jetpack Compose + Kotlin）
├── backend/          # Django + DRF 后端 API
├── docs/             # 架构、接口、部署与用户文档
├── infra/            # Nginx、生产部署、调度容器等基础设施配置
├── scripts/          # 开发与 CI 辅助脚本
└── test/             # API 集成测试
```

各子目录说明：

| 目录 | 说明 |
|------|------|
| [`android/`](android/) | 移动端应用，详见 [android/README.md](android/README.md) |
| [`backend/`](backend/) | REST API 服务，详见 [backend/README.md](backend/README.md) |
| [`docs/`](docs/) | 项目文档索引，详见 [docs/README.md](docs/README.md) |
| [`infra/`](infra/) | 生产环境配置与调度说明，详见 [infra/README.md](infra/README.md) |

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Android 客户端                          │
│  Compose UI → ViewModel → Repository → Retrofit / Room      │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS + JWT
┌──────────────────────────▼──────────────────────────────────┐
│                    Django 后端（单体多 App）                  │
│  users · tasks · daily · wallet · gacha · shop · ai · …     │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
        PostgreSQL                  LLM Provider
```

- **经济逻辑**（扣费、发奖、抽卡保底等）由服务端统一处理，客户端负责展示与交互。
- **货币状态**在 Android 端通过应用级 `CurrencyViewModel` 共享，保证各页面余额同步。
- **API 契约**基于 OpenAPI 3，由 `drf-spectacular` 自动生成，便于 Apifox 联调。

---

## 技术栈

### Android 客户端

| 层次 | 技术 |
|------|------|
| UI | Jetpack Compose |
| 语言 | Kotlin |
| 状态管理 | ViewModel + StateFlow / SharedFlow |
| 网络 | Retrofit + OkHttp + Coroutines |
| 本地存储 | Room、TokenManager（会话凭证） |
| 图片 | Coil |
| 后台任务 | WorkManager |

### Django 后端

| 层次 | 技术 |
|------|------|
| 框架 | Django 4.2 + Django REST Framework |
| 鉴权 | SimpleJWT（Access + Refresh Token） |
| 数据库 | PostgreSQL（生产）/ SQLite（本地开发） |
| API 文档 | drf-spectacular / OpenAPI 3 |
| AI | LangChain + LangGraph 风格工作流 |
| 部署 | Docker + Gunicorn + Nginx |

### 后端业务模块

| App | 职责 |
|-----|------|
| `common` | 公共中间件、异常处理、健康检查 |
| `users` | 注册登录、用户画像、邮箱验证 |
| `tasks` | 任务创建、完成、AI 定价与结算 |
| `daily` | 日常指标（作息、饮水等）评估与奖励 |
| `wallet` | 双轨货币余额与交易流水 |
| `gacha` | 抽卡逻辑、概率与保底 |
| `shop` | 商城商品、背包、愿望兑换 |
| `reports` | 报表 |
| `ai` | LLM Agent、Prompt 模板、工作流 |

API 统一前缀：`/api/v1/`。完整路由见 [`backend/config/urls.py`](backend/config/urls.py)。

---

## 快速开始

### 后端

```bash
cd backend
cp .env.example .env          # 按需修改环境变量
docker compose up -d db
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # 可选
python manage.py runserver
```

常用地址：

| 入口 | URL |
|------|-----|
| Swagger 文档 | http://127.0.0.1:8000/api/docs/ |
| OpenAPI Schema | http://127.0.0.1:8000/api/schema/ |
| Django Admin | http://127.0.0.1:8000/admin/ |

导出 OpenAPI 供 Apifox 导入：

```bash
curl http://127.0.0.1:8000/api/schema/ -o motiwish-openapi.yaml
```

JWT 请求头格式：`Authorization: Bearer <access_token>`

更多细节（AI 环境变量、邮件验证、Docker 全栈部署）见 [backend/README.md](backend/README.md) 与 [docs/api/后端本地部署指南.md](docs/api/后端本地部署指南.md)。

### Android

使用 Android Studio 打开 `android/` 目录，或命令行构建：

```bash
cd android
.\gradlew.bat assembleDebug    # Windows
./gradlew assembleDebug        # macOS / Linux
```

联调时将 `MainActivity` 中的 `baseUrl` 指向本地后端（默认可能指向远程测试服务器）。接口文档入口：http://127.0.0.1:8000/api/docs/

详见 [android/README.md](android/README.md)。

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [docs/MotiWish 愿动力 - 用户操作手册.md](docs/MotiWish%20愿动力%20-%20用户操作手册.md) | 产品功能与用户操作说明 |
| [docs/MotiWish 项目实现说明文档.md](docs/MotiWish%20项目实现说明文档.md) | 前后端实现细节与开发总结 |
| [docs/api/](docs/api/) | OpenAPI 协作、任务定价与愿望系统 AI 对接指南 |
| [docs/architecture/](docs/architecture/) | 系统架构、模块边界、数据模型 |
| [docs/deployment/](docs/deployment/) | 部署说明与运维步骤 |
| [infra/README.md](infra/README.md) | 生产环境、Nginx、每日愿望调度容器 |

---

## 协作约定

- **Android 团队** 主要维护 `android/`
- **后端团队** 主要维护 `backend/`
- **联调约定**、OpenAPI 导出与 Apifox 资料统一放在 `docs/api/`
- **部署配置** 统一归档到 `infra/` 与 `backend/deploy/`

---

## 当前状态

- [x] 后端首版就绪：用户、任务、钱包、抽卡、商城、AI 等核心模块
- [x] Android 客户端已并入 Monorepo，主要页面与后端 API 已对接
- [x] OpenAPI 文档与 Docker 本地开发环境可用
- [ ] 根级 CI、代码规范与 OpenAPI 导出归档（`docs/api/openapi/`）
- [ ] 生产部署流程与监控完善

---

## License

尚未指定。如需开源或商用，请补充 LICENSE 文件。
