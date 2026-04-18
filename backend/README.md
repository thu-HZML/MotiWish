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

## 环境变量

本地开发默认读取 `backend/.env`。模板见 `backend/.env.example`。
