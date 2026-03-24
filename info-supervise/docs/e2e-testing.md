# 端到端联调说明

本文档用于验证 `Info Supervise` 是否已经跑通以下完整链路：

`录入监控对象 -> 执行监控任务 -> 生成事件 -> 发送飞书通知`

同时覆盖版本更新通知能力。

## 前置条件

- 本机 Docker daemon 已启动
- `.env` 中已配置：

```env
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-id
FEISHU_SECRET=
```

如果飞书机器人启用了签名校验，再填写 `FEISHU_SECRET`。

## 启动容器

在项目根目录执行：

```bash
docker compose up --build -d
```

检查容器状态：

```bash
docker compose ps
```

期望看到：

- `api` 为 `healthy`
- `postgres` 为 `healthy`
- `redis` 为 `healthy`
- `worker` 为 `Up`

## 基础连通验证

打开以下地址：

- 页面：`http://localhost:8000/`
- Swagger：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`

健康检查应返回类似：

```json
{
  "status": "ok",
  "database": true,
  "redis": true
}
```

## 默认真实联调样例

建议使用这些公开样例：

- Google Play 包名：`com.supercell.clashofclans`
- App Store Bundle ID：`com.supercell.magic`
- App Store App ID：`529479190`
- 厂商：`Supercell`

## 联调步骤

### 1. 录入 Google Play 应用

在页面点击“填 GP 样例”，然后提交。

也可以用 API：

```bash
curl -X POST http://localhost:8000/watch/apps \
  -H "Content-Type: application/json" \
  -d '{
    "store": "google_play",
    "display_name": "Clash of Clans",
    "package_name": "com.supercell.clashofclans",
    "regions": ["US", "JP", "KR"],
    "notify_on_version_update": true
  }'
```

### 2. 录入 App Store 应用

在页面点击“填 App Store 样例”，然后提交。

也可以用 API：

```bash
curl -X POST http://localhost:8000/watch/apps \
  -H "Content-Type: application/json" \
  -d '{
    "store": "app_store",
    "display_name": "Clash of Clans",
    "bundle_id": "com.supercell.magic",
    "app_id": "529479190",
    "regions": ["US", "JP", "KR"],
    "notify_on_version_update": true
  }'
```

### 3. 录入厂商监控

在页面点击“填厂商样例”，然后提交。

也可以用 API：

```bash
curl -X POST http://localhost:8000/watch/publishers \
  -H "Content-Type: application/json" \
  -d '{
    "store": "app_store",
    "publisher_name": "Supercell",
    "regions": ["US", "JP"],
    "auto_add_apps": true,
    "auto_added_notify_on_version_update": true
  }'
```

### 4. 验证列表编辑与删除

页面验证：

- 在应用列表点击 `编辑`，确认表单切换为“编辑模式”
- 修改 `区域`、`监控状态`、`版本更新通知` 或 `检查间隔` 后保存
- 确认应用列表中对应记录已刷新，且 `当前版本` 列正常显示 `status.last_version`
- 在厂商列表点击 `编辑`，修改 `区域`、`自动纳管`、`自动纳管版本更新通知` 后保存
- 点击 `取消编辑`，确认表单恢复为新增模式
- 点击任一 `删除` 按钮并确认弹窗，确认该记录从列表中消失

API 验证：

```bash
curl -X PATCH http://localhost:8000/watch/apps/<app_id> \
  -H "Content-Type: application/json" \
  -d '{
    "regions": ["US", "JP"],
    "monitoring_enabled": true,
    "notify_on_version_update": true,
    "check_interval_minutes": 30
  }'
```

```bash
curl -X PATCH http://localhost:8000/watch/publishers/<publisher_id> \
  -H "Content-Type: application/json" \
  -d '{
    "regions": ["US", "JP"],
    "monitoring_enabled": true,
    "auto_add_apps": true,
    "auto_added_notify_on_version_update": true
  }'
```

```bash
curl -X DELETE http://localhost:8000/watch/apps/<app_id>
```

说明：

- 应用主标识 `package_name` / `bundle_id` / `app_id` 默认不支持直接修改
- 如需变更主标识，建议删除后重新创建

### 5. 验证列表分页

页面验证：

- 打开 `http://localhost:8000/`，确认应用列表和厂商列表底部有分页控件（上一页/下一页/首页/末页/每页条数选择）
- 当数据超过一页时，翻页确认列表刷新且"当前版本"列仍正常显示
- 切换"每页条数"后，列表自动回到第 1 页
- 删除当前页最后一条记录时，自动回退到上一页

API 验证：

```bash
curl "http://localhost:8000/watch/apps?page=1&page_size=10"
```

返回应包含 `items`、`total`、`page`、`page_size`、`total_pages` 字段。

```bash
curl "http://localhost:8000/watch/publishers?page=1&page_size=10"
```

### 6. 执行监控任务

建议按这个顺序：

```bash
curl -X POST http://localhost:8000/jobs/run \
  -H "Content-Type: application/json" \
  -d '{"job_name":"monitor_apps"}'
```

```bash
curl -X POST http://localhost:8000/jobs/run \
  -H "Content-Type: application/json" \
  -d '{"job_name":"discover_publishers"}'
```

```bash
curl -X POST http://localhost:8000/jobs/run \
  -H "Content-Type: application/json" \
  -d '{"job_name":"deliver_notifications"}'
```

页面也支持一键执行这些任务。

## 结果验证

### 查看最近事件

```bash
curl "http://localhost:8000/events?limit=20"
```

重点观察：

- 是否产生 `app_visible_first_seen`
- 是否产生 `publisher_new_game_detected`
- 如果版本变化，则是否产生 `app_version_updated`
- 通知类事件是否从 `pending` 变为 `sent`

### 查看任务执行记录

```bash
curl http://localhost:8000/jobs/runs
```

### 查看仪表盘摘要

```bash
curl http://localhost:8000/dashboard/summary
```

### 查看飞书

确认目标飞书群已经收到消息。

## 常见问题

### 1. Docker 启不来

报错类似：

```text
Cannot connect to the Docker daemon
```

处理方式：

- 启动 Docker Desktop
- 再执行 `docker compose up --build -d`

### 2. 页面能打开，但没有数据

处理方式：

- 先录入样例
- 再手动执行 `monitor_apps`
- 然后刷新页面

### 3. 飞书消息没发出去

处理方式：

- 检查 `FEISHU_WEBHOOK_URL`
- 检查机器人是否开启了关键词限制
- 如果开启签名校验，确认 `FEISHU_SECRET` 是否正确
- 查看 `GET /events` 中事件状态是否为 `failed`

### 4. 事件一直是 pending

说明通知投递还没执行。处理方式：

```bash
curl -X POST http://localhost:8000/jobs/run \
  -H "Content-Type: application/json" \
  -d '{"job_name":"deliver_notifications"}'
```

### 5. 某些区域没有查到应用

处理方式：

- 确认应用在该区域是否真的公开可见
- 先用 `US` 等主区域验证
- 再逐步扩展更多区域

### 6. 为什么没有版本更新事件

只有同时满足下面条件才会触发：

- 该应用开启了 `notify_on_version_update`
- 系统之前已经采集过旧版本号
- 本次抓取到的新版本号与旧版本号不同

如果是厂商自动纳管的新游戏，还需要厂商配置中开启：

- `auto_added_notify_on_version_update`
