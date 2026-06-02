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

2. 构建并启动：

```powershell
docker compose up -d --build
```

3. 访问：

- API 文档：`http://localhost/api/docs/`
- 管理后台：`http://localhost/admin/`
- 健康检查：`http://localhost/api/v1/common/health/`

默认 Nginx 配置为 HTTP-only，不需要证书，适合本地和安卓模拟器联调。安卓模拟器访问宿主机时使用 `http://10.0.2.2/`，并确保 `.env` 中 `DJANGO_ALLOWED_HOSTS` 包含 `10.0.2.2`。

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
DJANGO_ALLOWED_HOSTS=8.147.57.94,127.0.0.1,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=http://8.147.57.94,https://8.147.57.94
DJANGO_SESSION_COOKIE_SECURE=false
DJANGO_CSRF_COOKIE_SECURE=false
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

默认配置会通过 HTTP 提供服务，适合服务器端安卓联调：

```text
http://8.147.57.94/api/docs/
```

如果要启用 HTTPS，可以复制示例配置并准备证书：

```bash
cp deploy/nginx/examples/https.conf deploy/nginx/conf.d/default.conf
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

注意：自签证书不会被 Android/Java 默认信任。安卓端访问 HTTPS 自签服务时，需要额外配置 Network Security Config 或安装信任证书。更推荐为生产环境绑定域名并使用受信任 CA 证书；纯联调阶段建议使用 HTTP。

启用 HTTPS 后，再把 cookie 安全项改为：

```env
DJANGO_SESSION_COOKIE_SECURE=true
DJANGO_CSRF_COOKIE_SECURE=true
```

启动：

```bash
docker compose up -d --build
```

启动后检查 Django 实际读到的生产配置：

```bash
docker compose exec web python manage.py shell -c "from django.conf import settings; print('DEBUG=', settings.DEBUG); print('ALLOWED_HOSTS=', settings.ALLOWED_HOSTS); print('CSRF_TRUSTED_ORIGINS=', settings.CSRF_TRUSTED_ORIGINS)"
```

`ALLOWED_HOSTS` 至少应包含 `8.147.57.94`、`127.0.0.1` 和 `localhost`，`DEBUG` 应为 `False`。其中 `127.0.0.1` / `localhost` 用于容器内部 healthcheck。如果这里仍然只看到 `['127.0.0.1', 'localhost']`，说明服务器当前容器没有读到新的 `.env`，请重新检查部署目录下的 `.env` 文件并重建后端容器：

```bash
docker compose up -d --build web nginx
```

如果只修改了 Nginx 配置，可以重启 Nginx 容器：

```bash
docker compose restart nginx
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

默认 HTTP 管理后台地址：

```text
http://8.147.57.94/admin/
```
