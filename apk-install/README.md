# APK/APKS/AAB/XAPK 安装工具

这是一个基于 Django 的 Web 工具应用，用于在电脑上通过浏览器安装 Android APK、APKS、AAB 和 XAPK 文件到连接的手机设备。

## 功能特性

### 基础功能
- ✅ 检查电脑是否连接手机设备
- ✅ 检测电脑是否有 adb 环境
- ✅ 检测电脑是否有 java 环境
- ✅ 通过拖拽/或者选择文件上传 apk、apks、aab 文件
- ✅ 通过上传文件，自动进行安装
- ✅ 安装完成自动清理中间文件

### XAPK 功能
- ✅ 通过 URL 下载 XAPK 文件
- ✅ 自动读取 manifest.json 获取应用信息
- ✅ 自动以 package_name 命名下载的文件
- ✅ 支持从历史记录重新安装已下载的 XAPK
- ✅ 支持删除历史 XAPK 文件
- ✅ 下载的 XAPK 文件会保留，方便重复安装

### 界面功能
- ✅ 现代化的 UI 设计，美观易用
- ✅ 实时环境状态显示（ADB、Java、设备连接）
- ✅ 文件拖拽上传支持
- ✅ 下载和安装进度实时显示
- ✅ 分阶段安装进度展示
- ✅ 错误提示和成功提示

## 环境要求

### 必需工具

1. **ADB (Android Debug Bridge)**
   - 下载地址: https://developer.android.com/studio/releases/platform-tools
   - 确保 `adb` 命令在系统 PATH 中
   - 验证方法: 在终端运行 `adb version`

2. **Java JDK**
   - 版本: JDK 8 或更高
   - 确保 `java` 命令在系统 PATH 中
   - 用于运行 bundletool（AAB 文件转换需要）
   - 验证方法: 在终端运行 `java -version`

3. **bundletool** (仅安装 AAB 文件时需要)
   - 下载地址: https://github.com/google/bundletool/releases
   - 将 `bundletool.jar` 放置在项目根目录
   - 或者确保 `bundletool` 命令在系统 PATH 中

### Python 环境

- Python 3.8 或更高版本

## 快速开始

### 方式一：使用启动脚本（推荐）

```bash
# 给脚本添加执行权限（仅首次需要）
chmod +x run.sh

# 运行启动脚本
./run.sh
```

启动脚本会自动：
- 创建虚拟环境（如果不存在）
- 安装 Python 依赖
- 运行数据库迁移
- 启动开发服务器

### 方式二：手动安装

1. **克隆或下载项目**

```bash
cd apk-install
```

2. **创建虚拟环境（推荐）**

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **安装 Python 依赖**

```bash
pip install -r requirements.txt
```

4. **运行数据库迁移**

```bash
python manage.py migrate
```

5. **启动开发服务器**

```bash
python manage.py runserver
```

6. **访问应用**

打开浏览器访问: http://127.0.0.1:8000

## 使用说明

### 1. 连接设备

- 使用 USB 连接 Android 设备到电脑
- 在设备上启用"USB 调试"模式
  - 设置 → 关于手机 → 连续点击"版本号"7次启用开发者选项
  - 设置 → 开发者选项 → 启用"USB 调试"
- 首次连接时，在设备上授权电脑的调试请求（会弹出授权对话框）

### 2. 检查环境

页面会自动检查以下内容：
- **ADB 环境**: 显示绿色表示已安装，红色表示未检测到
- **Java 环境**: 显示绿色表示已安装，红色表示未检测到
- **设备连接**: 显示已连接的设备数量，点击"刷新"按钮可重新检测

### 3. 上传并安装文件

#### 方式一：直接上传安装（APK/APKS/AAB）

1. 拖拽文件到上传区域，或点击上传区域选择文件
2. 支持的文件格式：`.apk`、`.apks`、`.aab`
3. 文件上传成功后，点击"安装"按钮
4. 等待安装完成，会显示安装进度和阶段信息
5. 安装完成后会自动清理临时文件

#### 方式二：下载并安装 XAPK

1. 在"XAPK 下载安装"区域输入 XAPK 文件的下载地址
2. 点击"下载"按钮，会显示下载进度
3. 下载完成后，文件会自动以 `package_name.xapk` 命名
4. 点击"安装 XAPK"按钮进行安装
5. 安装完成后会清理临时解压文件，但保留 XAPK 文件

### 4. 历史文件管理

- 在"历史 XAPK 文件"区域可以查看所有已下载的 XAPK 文件
- 显示文件信息：文件名、大小、下载时间
- 点击"安装"按钮可以重新安装历史文件
- 点击"删除"按钮可以删除不需要的文件
- 点击"刷新列表"按钮可以手动更新列表

## 文件类型说明

### APK
- **说明**: Android 应用的标准安装包
- **安装方式**: 直接使用 `adb install` 安装
- **特点**: 最简单，无需额外处理

### APKS
- **说明**: Android App Bundle 的拆分安装包
- **安装方式**: 解压后使用 `adb install-multiple` 安装所有 APK
- **特点**: 支持 split APKs，可以包含多个架构的 APK

### AAB
- **说明**: Android App Bundle，Google Play 使用的格式
- **安装方式**: 
  1. 使用 bundletool 转换为 APKS
  2. 解压 APKS
  3. 安装所有 APK
- **特点**: 需要 bundletool 和 Java 环境

### XAPK
- **说明**: 特殊格式的 APK 文件，是一个 ZIP 压缩包
- **结构**: 
  - 包含 `manifest.json` 文件（应用信息）
  - 包含主 APK 文件（`package_name.apk`）
  - 可能包含 split APKs
- **安装方式**:
  1. 下载 XAPK 文件
  2. 解压并读取 manifest.json
  3. 提取所有 APK 文件
  4. 使用 `adb install-multiple` 安装
- **特点**: 
  - 文件会自动以 `package_name.xapk` 命名
  - 下载的文件会保留，方便重复安装

## 项目结构

```
apk-install/
├── apk_installer/          # Django 项目配置
│   ├── settings.py         # 项目设置
│   ├── urls.py            # 主 URL 路由
│   ├── wsgi.py            # WSGI 配置
│   └── asgi.py            # ASGI 配置
├── installer/              # 主应用
│   ├── views.py           # 视图函数（API 端点）
│   ├── utils.py           # 工具函数（环境检测、安装逻辑）
│   ├── urls.py            # 应用路由
│   └── apps.py            # 应用配置
├── templates/              # HTML 模板
│   └── installer/
│       └── index.html     # 主页面
├── media/                  # 媒体文件目录（自动创建）
│   ├── uploads/          # 上传的文件（临时）
│   └── xapk/             # 下载的 XAPK 文件（保留）
├── temp/                   # 临时文件目录（自动创建）
├── doc/                    # 文档目录
│   ├── aab_apk_apks_install.md
│   └── download_and_install_xapk.md
├── requirements.txt        # Python 依赖
├── run.sh                 # 启动脚本
├── manage.py              # Django 管理脚本
└── README.md              # 本文件
```

## API 接口文档

### 环境检测接口

#### GET /api/check-env
检查 ADB 和 Java 环境

**响应:**
```json
{
  "adb": {
    "available": true,
    "version": "Android Debug Bridge version 1.0.41",
    "error": null
  },
  "java": {
    "available": true,
    "version": "openjdk version \"11.0.16\"",
    "error": null
  }
}
```

#### GET /api/check-device
检查设备连接状态

**响应:**
```json
{
  "connected": true,
  "devices": ["device_id_1", "device_id_2"],
  "error": null
}
```

### 文件上传和安装接口

#### POST /api/upload
上传文件

**请求:**
- Content-Type: `multipart/form-data`
- 参数: `file` (文件，支持 .apk, .apks, .aab)

**响应:**
```json
{
  "success": true,
  "message": "文件上传成功",
  "file_path": "/path/to/file.apk",
  "file_name": "app.apk",
  "file_type": "apk",
  "error": null
}
```

#### POST /api/install
安装文件

**请求:**
```json
{
  "file_path": "/path/to/file.apk",
  "file_type": "apk"
}
```

**响应:**
```json
{
  "success": true,
  "message": "安装成功",
  "error": null
}
```

### XAPK 相关接口

#### POST /api/download-xapk
下载 XAPK 文件

**请求:**
```json
{
  "url": "https://example.com/app.xapk"
}
```

**响应:**
```json
{
  "success": true,
  "message": "下载成功",
  "file_path": "/path/to/com.example.app.xapk",
  "file_name": "com.example.app.xapk",
  "error": null
}
```

**说明**: 
- 文件会自动以 `package_name.xapk` 命名
- 如果文件已存在，会添加时间戳：`package_name_timestamp.xapk`

#### POST /api/install-xapk
安装 XAPK 文件

**请求:**
```json
{
  "file_path": "/path/to/com.example.app.xapk"
}
```

**响应:**
```json
{
  "success": true,
  "message": "安装成功",
  "error": null
}
```

#### GET /api/list-xapk
获取已下载的 XAPK 文件列表

**响应:**
```json
{
  "success": true,
  "files": [
    {
      "file_name": "com.example.app.xapk",
      "file_path": "/path/to/com.example.app.xapk",
      "file_size": 52428800,
      "download_time": "2024-01-15 10:30:00",
      "formatted_size": "50.00 MB"
    }
  ],
  "error": null
}
```

#### POST /api/delete-xapk
删除 XAPK 文件

**请求:**
```json
{
  "file_path": "/path/to/com.example.app.xapk"
}
```

**响应:**
```json
{
  "success": true,
  "message": "删除成功",
  "error": null
}
```

## 故障排除

### ADB 未检测到
- 确保已安装 Android Platform Tools
- 检查 `adb` 命令是否在系统 PATH 中
- 在终端运行 `adb version` 验证
- **macOS/Linux**: 可能需要添加到 `~/.bashrc` 或 `~/.zshrc`:
  ```bash
  export PATH=$PATH:/path/to/platform-tools
  ```
- **Windows**: 添加到系统环境变量 PATH

### Java 未检测到
- 确保已安装 JDK 8 或更高版本
- 检查 `java` 命令是否在系统 PATH 中
- 在终端运行 `java -version` 验证
- **macOS**: 可以使用 Homebrew 安装: `brew install openjdk`
- **Linux**: 使用包管理器安装: `sudo apt install openjdk-11-jdk`
- **Windows**: 下载并安装 Oracle JDK 或 OpenJDK

### 设备未连接
- 确保设备已通过 USB 连接
- 在设备上启用"USB 调试"
- 在设备上授权电脑的调试请求（首次连接会弹出对话框）
- 运行 `adb devices` 检查设备是否显示
- 如果设备显示为 `unauthorized`，需要在设备上点击"允许 USB 调试"
- 某些设备需要启用"USB 调试（安全设置）"

### AAB 安装失败
- 确保已下载 `bundletool.jar` 并放置在项目根目录
- 或确保 `bundletool` 命令在系统 PATH 中
- 确保 Java 环境正常
- 检查文件大小，确保下载完整

### XAPK 下载失败
- 检查 URL 是否正确
- 确保网络连接正常
- 检查服务器是否支持下载
- 如果下载中断，可以重新尝试

### XAPK 安装失败
- 确保 XAPK 文件完整（未损坏）
- 检查设备存储空间是否充足
- 确保设备已连接并授权
- 查看错误信息，可能是应用签名问题

### 文件上传失败
- 检查文件大小是否超过限制（默认 100MB）
- 确保文件格式正确（.apk, .apks, .aab）
- 检查服务器磁盘空间

## 注意事项

### 安全相关
- 只安装来自可信来源的应用
- XAPK 文件会保留在服务器上，注意隐私和安全
- 删除不需要的 XAPK 文件以节省空间

### 性能相关
- 安装 AAB 文件需要较长时间（需要转换）
- 大文件下载可能需要较长时间
- 确保有足够的磁盘空间用于临时文件

### 功能限制
- 安装 AAB 文件需要 bundletool，首次安装会生成临时密钥（仅用于签名）
- 临时文件会在安装完成后自动清理
- 上传的文件会在安装完成后自动删除（XAPK 除外）
- 同时只能安装一个应用

### 文件管理
- XAPK 文件会自动以 `package_name.xapk` 命名
- 如果同名文件已存在，会添加时间戳
- 历史文件列表按下载时间倒序排列
- 删除 XAPK 文件会永久删除，无法恢复

## 开发说明

### 技术栈
- **后端**: Django 4.2+, Django REST Framework
- **前端**: 原生 HTML/CSS/JavaScript
- **工具**: ADB, Java, bundletool

### 依赖包
- `Django>=4.2.0,<5.0.0`
- `djangorestframework>=3.14.0`
- `django-cors-headers>=4.0.0`

### 开发环境设置
```bash
# 安装开发依赖
pip install -r requirements.txt

# 运行开发服务器（带自动重载）
python manage.py runserver

# 运行数据库迁移
python manage.py migrate

# 创建超级用户（如需要）
python manage.py createsuperuser
```

### 代码结构说明
- `installer/utils.py`: 包含所有工具函数
  - 环境检测函数
  - 文件安装函数
  - XAPK 处理函数
- `installer/views.py`: 包含所有 API 视图函数
- `templates/installer/index.html`: 前端界面

## 常见问题

### Q: 为什么下载的 XAPK 文件以 package_name 命名？
A: 这样可以更方便地识别应用，避免使用随机文件名。文件名格式为 `{package_name}.xapk`。

### Q: 可以同时安装多个应用吗？
A: 不可以，需要等待当前安装完成后再安装下一个。

### Q: XAPK 文件会占用多少空间？
A: XAPK 文件会保留在 `media/xapk/` 目录中，不会自动删除。建议定期清理不需要的文件。

### Q: 支持哪些操作系统？
A: 理论上支持所有可以运行 Django 和 ADB 的操作系统，包括 Windows、macOS 和 Linux。

### Q: 可以远程访问吗？
A: 开发服务器默认只监听 127.0.0.1，如需远程访问，需要修改启动命令：
```bash
python manage.py runserver 0.0.0.0:8000
```
注意：生产环境请使用专业的 WSGI 服务器（如 Gunicorn）并配置 HTTPS。

## 更新日志

### v1.0.0
- ✅ 基础 APK/APKS/AAB 安装功能
- ✅ 环境检测功能
- ✅ 文件上传和安装
- ✅ XAPK 下载和安装功能
- ✅ 历史文件管理
- ✅ 进度展示功能
- ✅ 现代化 UI 设计

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

本项目仅供学习和个人使用。

## 联系方式

如有问题或建议，请提交 Issue。
