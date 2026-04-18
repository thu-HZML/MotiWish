# MotiWish Monorepo

MotiWish 是一个游戏化时间管理项目，计划同时承载安卓客户端与 Django 后端。

当前仓库已经重构为 monorepo 结构，便于前后端协作、文档归档与后续部署扩展。

## 目录结构

```text
MotiWish/
  android/                  # 安卓客户端工程入口
  backend/                  # Django + DRF + PostgreSQL 后端
  docs/                     # 架构、接口、部署文档
  infra/                    # 反向代理、生产部署与基础设施配置
  scripts/                  # 开发与 CI 辅助脚本
  README.md
```

## 当前状态

- `backend/` 已完成首版后端初始化并接入本地 Docker PostgreSQL
- `android/` 已并入安卓客户端工程
- `docs/` 已预留接口文档、架构文档、部署文档目录

## 快速开始

后端开发：

```bash
cd backend
docker compose up -d db
python manage.py migrate
python manage.py runserver
```

访问地址：

- API 文档：`http://127.0.0.1:8000/api/docs/`
- OpenAPI Schema：`http://127.0.0.1:8000/api/schema/`
- Django Admin：`http://127.0.0.1:8000/admin/`

## 协作建议

- 安卓团队主要维护 `android/`
- 后端团队主要维护 `backend/`
- 联调约定、OpenAPI 导出与 Apifox 资料统一放在 `docs/api/`
- 部署相关内容统一归档到 `infra/`

## 下一步

- 为仓库补充根级 CI、代码规范与生产部署配置
- 将最新 OpenAPI 导出文件放入 `docs/api/openapi/`
