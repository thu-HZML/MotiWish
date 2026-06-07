# MotiWish 项目实现说明文档
## Android 前端与 Django 后端系统架构与开发总结

---

## 1. 项目概述
MotiWish 是一款结合了任务驱动、自我管理与游戏化奖励机制的移动端应用程序。本项目旨在通过虚拟货币系统、商城兑换机制以及抽卡系统，提高用户的自我管理动力。系统采用前后端分离架构设计，前端基于现代化的 Android Jetpack Compose 框架，后端基于 Python Django REST Framework (DRF) 搭建，并整合了 AI 大语言模型进行动态用户画像和任务定价。

---

## 2. 技术栈架构

### 2.1 前端技术栈 
* **UI 框架**：完全基于 `Jetpack Compose` 的声明式 UI，实现响应式与自适应布局。
* **编程语言**：`Kotlin`
* **状态管理**：基于 `ViewModel`、`StateFlow` 和 `SharedFlow` 实现单向数据流 (UDF)。
* **网络与异步**：`Retrofit` + `OkHttp` 进行网络请求，结合 `Kotlin Coroutines` 处理异步操作。
* **本地存储**：使用 `Room` (SQLite) 用于本地数据管理，`SharedPreferences/DataStore` 管理用户会话凭证。
* **多媒体加载**：采用 `Coil` 框架实现图片与网络资源的高效异步加载。

### 2.2 后端技术栈 
* **核心框架**：`Python 3` + `Django` + `Django REST Framework`。
* **认证鉴权**：使用 `SimpleJWT` 提供高安全性双令牌（Access & Refresh）认证，并支持无缝续期。
* **数据库**：`PostgreSQL` / `SQLite` 用于关系型业务数据的持久化。
* **API 文档**：集成 `drf-spectacular` 依据 OpenAPI 3 规范自动生成 Swagger 在线调试文档。
* **AI 集成**：整合提示词工程与大型语言模型 (LLM)，动态处理自我探索画像及问卷分析。

---

## 3. 核心业务模块实现细节

### 3.1 游戏化货币体系
系统设计了一级货币（通用资产）与二级货币（激励资产）的双轨制经济系统。针对所有的消费、收入、兑换等行为，通过 `WalletTransaction` 模型生成不可篡改的账单流水。前端通过 `CurrencyViewModel` 在顶级作用域订阅数据变动，确保各个二级页面之间的资产余额状态保持完全同步。

### 3.2 抽卡系统与沉浸式体验
> **实现亮点**：
> 评估实际开发体验后，系统抛弃了枯燥的纯数据反馈，采用了基于原生 Jetpack Compose 的视觉动效设计。点击抽卡时拦截即时响应，强制加入 1.2 秒的延迟渲染。通过 `infiniteTransition.animateFloat` 与 `graphicsLayer` 高效操控 GPU 绘制，实现星光图标的无缝循环旋转与脉冲缩放，极大地拉满了随机概率玩法的悬念感和用户期待感。

### 3.3 商城与背包整合机制
在底层数据模型中，“虚拟道具（卡片）”存放在 `Inventory` 表，而“现实愿望（奖励）”存放在 `RedemptionRecord` 表。为避免破坏用户的感知完整性，前端进行了出色的 UI 层数据融合：
* **统一聚类**：将状态为待享受（`requested`）的愿望数据拦截提取。
* **视觉欺骗**：利用 `InventoryItemCard` 组件，将虚拟道具和现实愿望套用同一种 UI 卡片骨架，伪装成同一类“物品”陈列于统一的“背包”页面下。
* **逻辑解耦**：底层回调接口各司其职。当用户在背包中点击对应按钮时，虚拟卡片透传触发 `useItem` 接口，愿望凭证触发 `fulfillRecord` 接口。

### 3.4 异常统一拦截与报错净化
由于 DRF 默认在 400 Bad Request 响应时会暴露底层字段名和格式化符号（如 `["secondary余额不足。"]`），前端网络层封装了极具鲁棒性的字符串清洗方案：
* 通过捕获 Retrofit 抛出的 `HttpException`，拦截并提取 `errorBody()`。
* 结合正则表达式 `replace(Regex("[\[\]{}()"']"), "")` 暴力拆除 JSON 数据残留符号。
* 针对英文开发字段名（如 `username`, `secondary`）配置翻译和屏蔽映射，最终将生硬的代码报错转化为温暖的大白话提示。

---

## 4. 部署与环境说明
* **服务端**：采用 `Docker` 搭配 `docker-compose.yml` 实现一键式容器化部署。环境内置 Gunicorn 应用服务器与 Nginx 反向代理集群，并提供 SSL 自签名证书自动化脚本以保障传输链路安全。
* **移动端**：通过 Gradle Kotlin DSL 规范化依赖版本（`libs.versions.toml`），配置 ProGuard 混淆规则以加固应用包体体积及反编译安全性。

