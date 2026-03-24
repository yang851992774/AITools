# Info Supervise

用于监控游戏在 `Google Play` / `Apple App Store` 的公开上架状态、下架状态、版本更新，以及指定厂商的新游戏上架情况，并通过飞书推送事件通知。

## 功能

- 按 `package_name` 监控 Google Play 游戏。
- 按 `bundle_id` 或 `app_id` 监控 App Store 游戏。
- 监控指定厂商的新游戏发现，并可自动加入应用监控。
- 支持对应用版本更新进行监控并推送飞书通知。
- 保存快照、当前状态、事件流水、通知记录和任务执行日志。
- 支持 `FastAPI + APScheduler + PostgreSQL + Redis + Docker Compose` 部署。

## 快速启动

1. 启动 Docker Desktop 或本机 Docker daemon。
2. 根据需要修改 `.env` 中的配置，至少填入 `FEISHU_WEBHOOK_URL`。
3. 在项目根目录执行：

```bash
docker compose up --build -d
```

4. 服务启动后访问：

- 控制台页面：`http://localhost:8000/`
- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`

## 前端页面

根路径 `/` 提供一个零构建的简易控制台页面，支持：

- 录入 Google Play / App Store 应用监控
- 录入厂商监控
- 列表点击进入编辑模式，并回填到上方表单
- 删除应用/厂商监控对象
- 配置“版本更新通知”开关
- 配置监控启停、区域、检查间隔等可变字段
- 在应用列表直接查看当前版本号
- 手动触发 `monitor_apps` / `discover_publishers` / `deliver_notifications`
- 查看最近应用、厂商、事件和任务记录
- 应用列表和厂商列表支持服务端分页（上一页 / 下一页 / 每页条数切换）
- 一键填入默认真实联调样例

## `.env` 关键配置

- `FEISHU_WEBHOOK_URL`: 飞书群机器人 Webhook 地址，真实通知必填
- `FEISHU_SECRET`: 如果机器人启用了签名校验则填写，否则可留空
- `DEFAULT_REGIONS`: 默认监控区域，例如 `US,JP,KR,TW,HK`
- `APP_MONITOR_INTERVAL_MINUTES`: 应用监控轮询周期
- `PUBLISHER_MONITOR_INTERVAL_HOURS`: 厂商新游发现周期
- `NOTIFICATION_INTERVAL_MINUTES`: 通知投递周期

## 主要接口

- `POST /watch/apps`
- `GET /watch/apps?page=1&page_size=20`
- `PATCH /watch/apps/{id}`
- `DELETE /watch/apps/{id}`
- `POST /watch/publishers`
- `GET /watch/publishers?page=1&page_size=20`
- `PATCH /watch/publishers/{id}`
- `DELETE /watch/publishers/{id}`
- `GET /events`
- `GET /dashboard/summary`
- `GET /jobs/runs`
- `POST /jobs/run`

## 示例请求

```bash
curl -X POST http://localhost:8000/watch/apps \
  -H "Content-Type: application/json" \
  -d '{
    "store": "google_play",
    "package_name": "com.supercell.clashofclans",
    "regions": ["US", "JP", "KR"],
    "notify_on_version_update": true
  }'
```

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

```bash
curl -X PATCH http://localhost:8000/watch/apps/<app_id> \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Clash of Clans",
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
    "publisher_name": "Supercell",
    "publisher_url": "https://apps.apple.com/developer/supercell/id488106216",
    "regions": ["US", "JP"],
    "monitoring_enabled": true,
    "auto_add_apps": true,
    "auto_added_notify_on_version_update": true
  }'
```

```bash
curl -X DELETE http://localhost:8000/watch/apps/<app_id>
```

```bash
curl "http://localhost:8000/watch/apps?page=1&page_size=10"
```

```bash
curl "http://localhost:8000/watch/publishers?page=2&page_size=20"
```

```bash
curl "http://localhost:8000/events?status=pending&limit=20"
```

```bash
curl http://localhost:8000/dashboard/summary
```

## 默认真实联调样例

- Google Play: `com.supercell.clashofclans`
- App Store Bundle ID: `com.supercell.magic`
- App Store App ID: `529479190`
- 厂商: `Supercell`

## 完整联调建议顺序

1. 在 `.env` 中填好 `FEISHU_WEBHOOK_URL`。
2. 执行 `docker compose up --build -d`。
3. 打开 `http://localhost:8000/`。
4. 填入默认样例或你自己的目标。
5. 依次执行：
   - `monitor_apps`
   - `discover_publishers`
   - `deliver_notifications`
6. 在页面或 `GET /events` 中确认事件状态。
7. 在飞书群确认消息是否成功送达。

如果你希望监控版本更新：
- 新增应用时把 `notify_on_version_update` 设为 `true`
- 新增厂商时把 `auto_added_notify_on_version_update` 设为 `true`
- 当商店返回的版本号与当前已记录版本号不同，系统会生成 `app_version_updated` 事件并投递飞书

页面编辑/删除说明：
- 点击应用列表或厂商列表中的 `编辑`，会把当前记录回填到上方表单并切换到编辑模式
- 编辑模式下提交会调用 `PATCH`，取消编辑后恢复为新增模式
- 点击 `删除` 会先弹确认框，再调用 `DELETE`
- 应用主标识 `package_name` / `bundle_id` / `app_id` 默认不支持直接修改；如需变更，建议删除后重新创建

更详细的联调步骤见 `docs/e2e-testing.md`。

## 故障排查

- `Cannot connect to the Docker daemon`：先启动 Docker Desktop。
- 页面打不开但 `/docs` 正常：检查 `backend/app/main.py` 是否已挂载静态页面并重建镜像。
- 飞书不发消息：检查 `FEISHU_WEBHOOK_URL`、关键词限制、签名校验和群机器人安全策略。
- 事件一直是 `pending`：手动执行一次 `deliver_notifications`，再看 `GET /jobs/runs` 和 `GET /events`。
- 没看到版本更新通知：确认该监控对象已开启版本更新开关，并且之前已经采集到旧版本号。
- Google Play 或 App Store 无结果：确认包名、Bundle ID、App ID 是否正确，且目标区域确实公开可见。

## 说明

- “过审核”按商店公开可见性判断。
- 下架采用连续不可见确认，减少误报。
- 版本更新会生成独立的 `app_version_updated` 事件。
- 通知默认通过飞书群机器人 Webhook 发送。
