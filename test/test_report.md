# MotiWish 后端接口测试表 (共 60 个)

## 1. Common (公共服务)
- [x] **GET** `/api/v1/common/health/` - 健康检查
- [x] **GET** `/api/v1/common/legal-documents/` - 获取法律与隐私文档

## 2. Users (用户与认证)
- [x] **POST** `/api/v1/users/auth/register/` - 用户注册
- [x] **POST** `/api/v1/users/auth/login/` - 用户登录
- [x] **POST** `/api/v1/users/auth/refresh/` - 刷新 JWT
- [x] **GET** `/api/v1/users/me/` - 获取当前用户基础资料
- [x] **PATCH** `/api/v1/users/me/` - 更新当前用户基础资料
- [x] **GET** `/api/v1/users/profile/meta/` - 获取画像元信息
- [x] **GET** `/api/v1/users/profile/prompts/` - 获取画像提醒状态
- [x] **POST** `/api/v1/users/profile/prompts/ack/` - 记录画像提醒已展示
- [x] **GET** `/api/v1/users/profile/stable/` - 获取稳定画像问卷结果
- [x] **PATCH** `/api/v1/users/profile/stable/` - 提交或更新稳定画像问卷
- [x] **GET** `/api/v1/users/profile/dynamic/` - 获取动态状态画像
- [x] **PATCH** `/api/v1/users/profile/dynamic/` - 提交或更新动态状态画像

## 3. Wallet (钱包模块)
- [x] **GET** `/api/v1/wallet/` - 获取钱包余额
- [x] **GET** `/api/v1/wallet/transactions/` - 获取钱包流水
- [x] **POST** `/api/v1/wallet/debt-reset/` - 执行一级货币债务重置

## 4. Reports (报表模块)
- [x] **GET** `/api/v1/reports/dashboard/` - 获取仪表盘报表

## 5. Tasks (任务模块)
- [x] **GET** `/api/v1/tasks/tasks/pricing/meta/` - 获取任务定价元信息
- [x] **GET** `/api/v1/tasks/tasks/` - 获取任务列表
- [x] **POST** `/api/v1/tasks/tasks/` - 创建任务
- [x] **GET** `/api/v1/tasks/tasks/{id}/` - 获取单个任务
- [x] **DELETE** `/api/v1/tasks/tasks/{id}/` - 删除任务
- [ ] **PUT** `/api/v1/tasks/tasks/{id}/` - 全量更新任务
- [ ] **PATCH** `/api/v1/tasks/tasks/{id}/` - 部分更新任务
- [ ] **POST** `/api/v1/tasks/tasks/{id}/complete/` - 完成并结算任务
- [ ] **POST** `/api/v1/tasks/tasks/{id}/pricing/apply/` - 应用任务定价结果
- [ ] **POST** `/api/v1/tasks/tasks/{id}/pricing/request/` - 发起任务 AI 定价请求
- [ ] **POST** `/api/v1/tasks/tasks/pricing/preview/` - 预览任务定价请求载荷
- [ ] **GET** `/api/v1/tasks/tasks/history/` - 获取任务历史记录
- [ ] **GET** `/api/v1/tasks/tasks/today/` - 获取指定日期的任务实例

## 6. Shop (商店与库存)
- [x] **GET** `/api/v1/shop/items/meta/` - 获取商店元信息
- [x] **GET** `/api/v1/shop/inventory/` - 获取库存列表
- [ ] **GET** `/api/v1/shop/items/pricing/meta/` - 获取愿望定价元信息 *(注：目前报 404)*
- [ ] **GET** `/api/v1/shop/items/` - 获取商店商品列表
- [ ] **POST** `/api/v1/shop/items/` - 创建商店商品
- [ ] **GET** `/api/v1/shop/items/{id}/` - 获取单个商店商品
- [ ] **PUT** `/api/v1/shop/items/{id}/` - 更新商店商品
- [ ] **PATCH** `/api/v1/shop/items/{id}/` - 部分更新商店商品
- [ ] **DELETE** `/api/v1/shop/items/{id}/` - 删除商店商品
- [ ] **POST** `/api/v1/shop/items/pricing/preview/` - 预览价格边界裁剪
- [ ] **POST** `/api/v1/shop/items/{id}/redeem/` - 购买商店商品
- [ ] **GET** `/api/v1/shop/redemptions/` - 获取兑换/购买记录
- [ ] **GET** `/api/v1/shop/redemptions/{id}/` - 获取单条兑换/购买记录
- [ ] **POST** `/api/v1/shop/redemptions/{id}/fulfill/` - 兑现愿望奖励记录
- [ ] **POST** `/api/v1/shop/redemptions/{id}/reject/` - 拒绝愿望奖励记录
- [ ] **GET** `/api/v1/shop/inventory/{id}/` - 获取单个库存道具
- [ ] **POST** `/api/v1/shop/inventory/{id}/use/` - 使用库存道具

## 7. Gacha (抽卡系统)
- [x] **GET** `/api/v1/gacha/pools/` - 获取卡池列表
- [ ] **GET** `/api/v1/gacha/pools/{id}/` - 获取单个卡池
- [ ] **POST** `/api/v1/gacha/pools/{id}/draw/` - 执行抽卡
- [ ] **GET** `/api/v1/gacha/pools/{id}/state/` - 查看当前卡池保底状态
- [ ] **GET** `/api/v1/gacha/records/` - 获取抽卡记录
- [ ] **GET** `/api/v1/gacha/records/{id}/` - 获取单条抽卡记录

## 8. AI (AI 服务)
- [ ] **GET** `/api/v1/ai/report-jobs/` - 获取 AI 报告任务列表
- [ ] **POST** `/api/v1/ai/report-jobs/` - 创建 AI 报告任务
- [ ] **GET** `/api/v1/ai/report-jobs/{id}/` - 获取单个 AI 报告任务
- [ ] **PUT** `/api/v1/ai/report-jobs/{id}/` - 全量更新 AI 报告任务
- [ ] **PATCH** `/api/v1/ai/report-jobs/{id}/` - 部分更新 AI 报告任务
- [ ] **DELETE** `/api/v1/ai/report-jobs/{id}/` - 删除 AI 报告任务