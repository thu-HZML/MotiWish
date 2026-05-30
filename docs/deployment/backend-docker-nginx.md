# Backend Docker + Nginx 部署

本文档默认在 `backend/` 目录执行命令。

## 本地启动

1. 复制环境变量：

```powershell
Copy-Item .env.example .env
```

如果只是临时本地验证，也可以不复制 `.env`，启动前设置：

```powershell
$env:MOTIWISH_ENV_FILE=".env.example"
```

2. 生成本地 HTTPS 自签名证书：

```powershell
.\deploy\scripts\create-self-signed-cert.ps1
```

3. 构建并启动：

```powershell
docker compose up -d --build
```

4. 访问：

- API 文档：`https://localhost/api/docs/`
- 管理后台：`https://localhost/admin/`
- 健康检查：`https://localhost/api/v1/common/health/`

浏览器会提示自签名证书不受信任，开发验证时选择继续访问即可。

## 服务器首次部署

服务器地址：`8.147.57.94`

服务器部署目录建议为：

```bash
/opt/motiwish/backend
```

服务器 `.env` 至少应包含：

```env
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=8.147.57.94
DJANGO_CSRF_TRUSTED_ORIGINS=https://8.147.57.94
DJANGO_SESSION_COOKIE_SECURE=true
DJANGO_CSRF_COOKIE_SECURE=true
TIME_ZONE=Asia/Shanghai

DB_ENGINE=django.db.backends.postgresql
POSTGRES_DB=motiwish
POSTGRES_USER=motiwish_user
POSTGRES_PASSWORD=replace-with-a-strong-password
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_CONN_MAX_AGE=60

HTTP_PORT=80
HTTPS_PORT=443

AI_PROVIDER=mock
AI_MODEL=mock-gpt
AI_API_KEY=
AI_BASE_URL=
AI_TEMPERATURE=0.2
AI_TIMEOUT=60
AI_MAX_RETRIES=2
```

生成服务器 IP 自签名证书：

```bash
mkdir -p deploy/nginx/certs
openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout deploy/nginx/certs/privkey.pem \
  -out deploy/nginx/certs/fullchain.pem \
  -subj "/CN=8.147.57.94" \
  -addext "subjectAltName=IP:8.147.57.94"
```

启动：

```bash
docker compose up -d --build
```

创建或重置超级用户：

```bash
docker compose exec web python manage.py shell -c "from apps.users.models import User; u, _ = User.objects.get_or_create(username='lsmd', defaults={'email':'lsmd23@mails.tsinghua.edu.cn'}); u.email='lsmd23@mails.tsinghua.edu.cn'; u.is_staff=True; u.is_superuser=True; u.set_password('101124'); u.save()"
```

## 维护命令

查看容器状态：

```bash
docker compose ps
```

查看后端日志：

```bash
docker compose logs -f web
```

查看 Nginx 日志：

```bash
docker compose logs -f nginx
```

查看数据库日志：

```bash
docker compose logs -f db
```

进入后端容器：

```bash
docker compose exec web sh
```

执行迁移：

```bash
docker compose exec web python manage.py migrate
```

收集静态文件：

```bash
docker compose exec web python manage.py collectstatic --noinput
```

重启服务：

```bash
docker compose restart
```

重新构建后端镜像并启动：

```bash
docker compose up -d --build
```

清空部署和数据库数据：

```bash
docker compose down -v
```

管理后台地址：

```text
https://8.147.57.94/admin/
```
