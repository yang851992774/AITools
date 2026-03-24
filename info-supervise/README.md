# Info Supervise

用于监控游戏在 `Google Play` / `Apple App Store` 的公开上架状态、下架状态、版本更新，以及指定厂商的新游戏上架情况，并通过飞书推送事件通知。

## 功能

- 按 `package_name` 监控 Google Play 游戏。
- 按 `bundle_id` 或 `app_id` 监控 App Store 游戏。
- 监控指定厂商的新游戏发现，并可自动加入应用监控。
- 支持对应用版本更新进行监控并推送飞书通知。
- **采集评分、评分人数、价格、更新日志、文件大小、最近更新时间等商店元数据。**
- **评分变动检测**：当评分变化幅度 ≥ 0.2 时产生 `app_rating_changed` 事件。
- **更新日志变动检测**：`release_notes` 内容变化时产生 `app_release_notes_changed` 事件。
- **飞书 Interactive Card 卡片通知**：包含应用信息、事件详情和商店按钮。
- **应用标签系统**：支持给应用打标签（如"竞品"、"重点关注"）并按标签筛选。
- **历史趋势图表**：点击应用名可查看版本/快照时间线图表。
- **每日摘要报告**：可配置定时发送 24h 内事件汇总到飞书。
- **事件筛选增强**：事件列表支持按类型、状态筛选，并支持分页。
- **应用搜索**：支持按名称 / 包名 / Bundle ID 模糊搜索。
- **CSV 导出**：一键导出应用列表为 CSV 文件。
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

- 录入 Google Play / App Store 应用监控（含标签输入）
- 录入厂商监控
- 列表点击进入编辑模式，并回填到上方表单
- 删除应用/厂商监控对象
- 配置"版本更新通知"开关
- 配置监控启停、区域、检查间隔等可变字段
- 应用列表显示评分、评分人数、当前版本、标签
- 点击应用名称弹出历史趋势图表（Chart.js）
- 应用列表支持按商店类型 / 标签筛选，支持模糊搜索
- 应用列表每行支持"商店"按钮，一键跳转到对应商店详情页
- 一键导出 CSV
- 手动触发 `monitor_apps` / `discover_publishers` / `deliver_notifications` / `generate_digest`
- 事件列表支持类型筛选、状态筛选和分页
- 应用列表和厂商列表支持服务端分页
- 一键填入默认真实联调样例

## `.env` 关键配置

- `FEISHU_WEBHOOK_URL`: 飞书群机器人 Webhook 地址，真实通知必填
- `FEISHU_SECRET`: 如果机器人启用了签名校验则填写，否则可留空
- `DEFAULT_REGIONS`: 默认监控区域，例如 `US,JP,KR,TW,HK`
- `APP_MONITOR_INTERVAL_MINUTES`: 应用监控轮询周期
- `PUBLISHER_MONITOR_INTERVAL_HOURS`: 厂商新游发现周期
- `NOTIFICATION_INTERVAL_MINUTES`: 通知投递周期
- `DIGEST_ENABLED`: 是否启用每日摘要报告（`true` / `false`）
- `DIGEST_HOUR`: 摘要报告发送时间（UTC 小时，默认 10）

## 主要接口

- `POST /watch/apps`
- `GET /watch/apps?page=1&page_size=20&store=google_play&q=clash&tag=竞品`
- `GET /watch/apps/export?store=google_play&q=clash&tag=竞品`（CSV 导出）
- `GET /watch/apps/{id}/history?days=30`（历史快照）
- `PATCH /watch/apps/{id}`
- `DELETE /watch/apps/{id}`
- `POST /watch/publishers`
- `GET /watch/publishers?page=1&page_size=20`
- `PATCH /watch/publishers/{id}`
- `DELETE /watch/publishers/{id}`
- `GET /events`（兼容旧接口）
- `GET /events/paged?page=1&page_size=20&event_type=app_version_updated&status=sent`
- `GET /dashboard/summary`
- `GET /jobs/runs`
- `POST /jobs/run`（支持 `generate_digest` 任务）

## 示例请求

```bash
curl -X POST http://localhost:8000/watch/apps \
  -H "Content-Type: application/json" \
  -d '{
    "store": "google_play",
    "package_name": "com.supercell.clashofclans",
    "regions": ["US", "JP", "KR"],
    "notify_on_version_update": true,
    "tags": ["竞品", "重点"]
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
curl "http://localhost:8000/watch/apps?page=1&page_size=10&store=google_play&q=clash&tag=竞品"
```

```bash
curl "http://localhost:8000/watch/apps/export" -o apps.csv
```

```bash
curl "http://localhost:8000/watch/apps/<app_id>/history?days=30"
```

```bash
curl "http://localhost:8000/events/paged?page=1&page_size=20&event_type=app_version_updated"
```

```bash
curl -X POST http://localhost:8000/jobs/run \
  -H "Content-Type: application/json" \
  -d '{"job_name": "generate_digest"}'
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
   - `generate_digest`（可选，生成 24h 汇总日报）
6. 在页面或 `GET /events/paged` 中确认事件状态。
7. 在飞书群确认消息是否成功送达（消息格式为卡片）。

新增监控能力说明：
- 评分变动：系统会在评分变化 ≥ 0.2 时生成 `app_rating_changed` 事件
- 更新日志：当 `release_notes` 内容变化时生成 `app_release_notes_changed` 事件
- 飞书通知现在使用 Interactive Card 格式，包含图标、关键字段和商店跳转按钮

页面编辑/删除说明：
- 点击应用列表或厂商列表中的 `编辑`，会把当前记录回填到上方表单并切换到编辑模式
- 编辑模式下提交会调用 `PATCH`，取消编辑后恢复为新增模式
- 点击 `删除` 会先弹确认框，再调用 `DELETE`

商店筛选、搜索与导出：
- 应用列表标题旁的下拉框可按 `Google Play` / `App Store` 过滤，切换后自动回到第 1 页
- 搜索框支持按应用名 / 包名 / Bundle ID 模糊搜索
- 标签下拉框可按标签筛选
- "导出 CSV" 按钮导出当前筛选条件下的全部应用
- 点击应用名称打开历史趋势弹窗，显示版本时间线图表

更详细的联调步骤见 `docs/e2e-testing.md`。

## 故障排查

- `Cannot connect to the Docker daemon`：先启动 Docker Desktop。
- 页面打不开但 `/docs` 正常：检查 `backend/app/main.py` 是否已挂载静态页面并重建镜像。
- 飞书不发消息：检查 `FEISHU_WEBHOOK_URL`、关键词限制、签名校验和群机器人安全策略。
- 事件一直是 `pending`：手动执行一次 `deliver_notifications`，再看 `GET /jobs/runs` 和 `GET /events`。
- 没看到版本更新通知：确认该监控对象已开启版本更新开关，并且之前已经采集到旧版本号。
- Google Play 或 App Store 无结果：确认包名、Bundle ID、App ID 是否正确，且目标区域确实公开可见。

## 说明

- "过审核"按商店公开可见性判断。
- 下架采用连续不可见确认，减少误报。
- 版本更新会生成独立的 `app_version_updated` 事件。
- 评分变动会生成 `app_rating_changed` 事件（阈值 0.2）。
- 更新日志变动会生成 `app_release_notes_changed` 事件。
- 通知默认通过飞书群机器人 Webhook 发送（Interactive Card 卡片格式）。
