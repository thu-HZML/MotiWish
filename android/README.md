# MotiWish Android

此目录已并入 MotiWish 安卓客户端工程，作为 monorepo 中的前端应用部分。

## 当前结构

```text
android/
  app/
  gradle/
  build.gradle.kts
  gradle.properties
  gradlew
  gradlew.bat
  settings.gradle.kts
```

## 本地开发

如果使用 Android Studio，直接打开 `android/` 目录即可。

命令行构建示例：

```bash
cd android
.\gradlew.bat assembleDebug
```

## 与后端联调

后端项目位于 `../backend/`，接口文档入口见：

- `http://127.0.0.1:8000/api/docs/`

建议将联调约定和接口导出统一归档到 `../docs/api/`。
