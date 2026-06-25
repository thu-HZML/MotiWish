# 本地联调与测试流程（Android + Django）

本文档用于日常开发联调：先起后端，再跑 Android，最后做最小冒烟验证。默认在 Windows + Android Studio + Docker Desktop 环境下执行。

## 1. 前置环境检查（首次或环境变更后执行）

在仓库根目录 `MotiWish/`：

```powershell
java -version
docker --version
docker compose version
```

在 `android/` 目录：

```powershell
.\gradlew.bat -v
```

建议基线：

- JDK 17
- Android Gradle Wrapper 可正常拉起
- Docker / Compose 可用

如果 `adb`、`emulator` 不在 PATH，可直接用 SDK 绝对路径执行（示例）：

```powershell
D:\AndroidAppData\platform-tools\adb.exe devices
D:\AndroidAppData\emulator\emulator.exe -list-avds
```

## 2. 启动本地后端（Docker）

工作目录切到 `backend/`。

1) 准备环境变量：

```powershell
Copy-Item .env.example .env
```

2) 确认允许模拟器访问（`10.0.2.2`）：

```env
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,10.0.2.2
```

3) 启动容器：

```powershell
docker compose up -d --build
docker compose ps
```

4) 健康检查（容器内）：

```powershell
docker compose exec -T web python -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/common/health/', timeout=5).read().decode())"
```

## 3. Nginx 证书处理（仅本地需要时）

如果 `docker compose ps` 中 `nginx` 重启，且日志提示缺少 `fullchain.pem`/`privkey.pem`，生成本地自签证书：

```powershell
openssl req -x509 -nodes -newkey rsa:2048 -days 365 `
  -keyout deploy/nginx/certs/privkey.pem `
  -out deploy/nginx/certs/fullchain.pem `
  -subj "/CN=127.0.0.1" `
  -addext "subjectAltName=IP:127.0.0.1,IP:10.0.2.2"

docker compose restart nginx
docker compose ps
```

备注：自签证书仅用于本地联调，不建议生产使用。

## 4. Android 本地联调

1) 用 Android Studio 打开 `android/` 目录。  
2) 选择模拟器（如 `Pixel_9a`）并启动。  
3) 确认 App 请求地址和后端一致：

- 优先使用模拟器访问宿主机：`http://10.0.2.2/`（或你实际启用的 `https://10.0.2.2/`）
- 若使用 HTTPS 自签证书，需额外处理 Android 证书信任问题；联调阶段更建议 HTTP

4) 命令行构建（可选）：

```powershell
cd ..\android
.\gradlew.bat assembleDebug
```

## 5. 最小测试清单（每次联调前后）

后端：

```powershell
cd ..\backend
docker compose ps
docker compose logs --tail 100 web
```

Android：

```powershell
cd ..\android
.\gradlew.bat testDebugUnitTest
```

联调验收建议：

- App 可正常登录/鉴权
- 任务列表和新增任务可用
- 钱包余额、抽卡、商城接口返回正常
- 后端无连续 5xx 错误

## 6. 常见问题排查

- `adb/emulator` 命令不存在：使用 SDK 绝对路径，或把 `platform-tools`、`emulator` 加入 PATH。
- `nginx` 循环重启：先看 `docker compose logs nginx`，通常是证书或配置文件缺失。
- Android 无法访问本机后端：确认使用 `10.0.2.2`，并检查 `DJANGO_ALLOWED_HOSTS`。
- Docker 服务异常：重启 Docker Desktop 后执行 `docker compose up -d`。

## 7. 与云端部署衔接

本地联调通过后再上云，推荐顺序：

1) 确认本地冒烟通过  
2) 通知待部署分支  
3) 服务器执行 git 同步 + docker 重建  
4) 云端健康检查 + Android 回归验证
