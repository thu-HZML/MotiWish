# 愿望系统 AI 对接指南

## 1. 功能概览

愿望系统现在支持两类 AI 候选：

- 用户手动输入愿望，后端 AI 判断档位并给出精确定价。
- 后端每日刷新一个愿望候选，结合用户画像、近期任务、历史愿望，并给刷新候选适度折扣以增强正反馈。

两类候选都不会直接创建商店商品。前端需要让用户确认，确认后才会创建用户私有的愿望商品，并出现在商店商品列表中。

## 2. 手动愿望定价

`POST /api/v1/ai/wish-pricing-sessions/`

请求：

```json
{
  "wish_payload": {
    "title": "周末去吃一顿喜欢的餐厅",
    "description": "完成本周计划后作为奖励。",
    "tags": ["food", "rest"]
  }
}
```

响应中的关键字段：

```json
{
  "id": 12,
  "source": "manual",
  "status": "waiting_confirmation",
  "wish_payload": {},
  "quote_payload": {
    "title": "周末去吃一顿喜欢的餐厅",
    "description": "完成本周计划后作为奖励。",
    "price_tier": "medium",
    "price_secondary": 235,
    "rarity": "rare",
    "inventory": 1,
    "reasoning": "...",
    "pricing_bounds": {
      "price_secondary": {
        "min": 120,
        "max": 350,
        "recommended": 235
      },
      "price_tier": "medium"
    }
  }
}
```

前端建议展示：

- `quote_payload.title`
- `quote_payload.description`
- `quote_payload.price_tier`
- `quote_payload.price_secondary`
- `quote_payload.reasoning`
- `quote_payload.user_fit_notes`

## 3. 每日刷新愿望候选

`POST /api/v1/ai/wish-pricing-sessions/daily-refresh/`

请求为空即可：

```json
{}
```

同一用户同一天默认只会生成一次。若需要强制重刷：

```json
{
  "force": true
}
```

也可以指定日期：

```json
{
  "refresh_date": "2026-06-06"
}
```

返回结构与手动愿望定价一致，区别是：

- `source = daily_refresh`
- `refresh_date` 有值
- `quote_payload.user_fit_notes` 会提示刷新候选存在轻微反馈折扣

## 4. 确认或取消候选

`POST /api/v1/ai/wish-pricing-sessions/{id}/confirm/`

确认创建商店商品：

```json
{
  "action": "accept"
}
```

确认后：

- 会话状态变为 `accepted`
- `generated_item` 返回新创建的商店商品
- 商品 `owner` 为当前用户
- 商品 `category` 为 `wish`
- 商品只会出现在当前用户自己的商店列表里

取消候选：

```json
{
  "action": "cancel"
}
```

取消后不会创建商品。

## 5. 查询候选

列表：

`GET /api/v1/ai/wish-pricing-sessions/`

详情：

`GET /api/v1/ai/wish-pricing-sessions/{id}/`

前端可以用 `status` 过滤本地展示逻辑：

- `waiting_confirmation`：待用户确认
- `accepted`：已创建商品
- `cancelled`：用户取消
- `failed`：生成失败

## 6. 商品列表

确认后的愿望商品继续使用原商店接口获取：

`GET /api/v1/shop/items/?category=wish_reward`

## 7. 后端每日固定时间刷新

后端提供 management command：

```bash
python manage.py generate_daily_wishes
```

指定日期：

```bash
python manage.py generate_daily_wishes --date 2026-06-06
```

只为单个用户生成：

```bash
python manage.py generate_daily_wishes --user-id 1
```

部署时可用 cron、Kubernetes CronJob 或服务器定时任务在固定时间调用该命令。
