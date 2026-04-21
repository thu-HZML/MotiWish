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

如果你希望拿到带鉴权接口定义的完整规范，建议先确保数据库迁移完成，再导入这个文件。

JWT 鉴权请求头格式：

```http
Authorization: Bearer <access_token>
```

## 环境变量

本地开发默认读取 `backend/.env`。模板见 `backend/.env.example`。
