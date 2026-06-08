# Infrastructure

此目录用于归档生产环境相关配置，例如：

- Nginx 配置
- 生产版 Docker Compose
- 进程守护或 systemd 配置

## 愿望每日刷新调度容器

后端 `docker-compose.yml` 已包含 `scheduler` 服务，用于每天固定时间生成 AI 愿望候选。

### 工作方式

`scheduler` 复用后端镜像 `motiwish-backend:latest`，启动后执行：

```bash
/app/deploy/scripts/daily-wish-scheduler.sh
```

脚本会：

1. 等待 PostgreSQL 可用。
2. 按 `TZ` 和 `DAILY_WISH_REFRESH_TIME` 计算下一次触发时间。
3. 到点执行：

```bash
python manage.py generate_daily_wishes
```

该命令会为每个 active 用户生成一个当天的待确认愿望候选。同一用户同一天默认幂等，不会重复生成。

### 环境变量

可在云端 `.env` 或 compose 环境变量中配置：

```env
SCHEDULER_TZ=Asia/Shanghai
DAILY_WISH_REFRESH_TIME=08:00
DAILY_WISH_FORCE=false
```

说明：

- `SCHEDULER_TZ`：调度时区，默认 `Asia/Shanghai`。
- `DAILY_WISH_REFRESH_TIME`：每日触发时间，格式 `HH:MM`，默认 `08:00`。
- `DAILY_WISH_FORCE`：是否每天强制重刷已有候选，默认 `false`。生产环境通常保持 `false`。

### 云端部署

在服务器上进入后端目录：

```bash
cd /path/to/MotiWish/backend
```

构建并启动：

```bash
docker compose build
docker compose up -d db web scheduler nginx
```

查看状态：

```bash
docker compose ps
```

查看调度日志：

```bash
docker compose logs -f scheduler
```

### 手动触发一次

方式一：直接执行 management command，推荐用于测试：

```bash
docker compose exec -T web python manage.py generate_daily_wishes
```

只为某个用户生成：

```bash
docker compose exec -T web python manage.py generate_daily_wishes --user-id 1
```

强制重刷：

```bash
docker compose exec -T web python manage.py generate_daily_wishes --user-id 1 --force
```

指定日期：

```bash
docker compose exec -T web python manage.py generate_daily_wishes --date 2026-06-06 --user-id 1 --force
```

方式二：用 scheduler 容器跑一次完整调度脚本：

```bash
docker compose run --rm \
  -e DAILY_WISH_RUN_ON_START=true \
  -e SCHEDULER_RUN_ONCE=true \
  scheduler
```

### 临时调整触发时间测试

例如临时设置为北京时间 15:30：

```bash
DAILY_WISH_REFRESH_TIME=15:30 docker compose up -d scheduler
```

或者修改 `.env` 后重启：

```bash
docker compose up -d --force-recreate scheduler
```

### 维护命令

重启调度容器：

```bash
docker compose restart scheduler
```

停止调度容器：

```bash
docker compose stop scheduler
```

更新代码后重新部署：

```bash
git pull
docker compose build
docker compose up -d
```

清理一次性测试容器：

```bash
docker compose rm -f
```

### 注意事项

- `scheduler` 不负责执行数据库迁移和静态文件收集，这些仍由 `web` 启动时完成。
- 生产环境建议保持 `DAILY_WISH_FORCE=false`，避免每天覆盖用户尚未处理的候选。
- 若服务器本身是 UTC，不影响调度；容器内通过 `SCHEDULER_TZ=Asia/Shanghai` 按北京时间计算。
