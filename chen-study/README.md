# 小学数学练习题生成器

一个基于 React + Django 的小学数学练习题生成工具，可以生成加减乘除运算题目，支持填写结果或填写中间值，并导出为PDF文件。

## 功能特性

- ✅ 生成N页M以内的加减乘除数学题目
- ✅ 支持表内乘除法（1-9）
- ✅ 支持混合运算：
  - 加乘（先乘后加）：a + b × c
  - 加除（先除后加）：a + b ÷ c
  - 减乘（先乘后减）：a - b × c
  - 减除（先除后减）：a - b ÷ c
- ✅ 支持两种题目类型：
  - 填写运算结果
  - 填写中间值（加数、减数、乘数、除数、被除数、被减数等）
- ✅ 生成PDF文件用于打印（自动生成题目和答案两份PDF，打包为ZIP下载）
- ✅ 预览功能，生成前可查看效果
- ✅ 美观的排列格式（每页60题，3列20行布局，优化间距适合A4打印）

## 技术栈

- **前端**: React 18
- **后端**: Django 4.2 + Django REST Framework
- **PDF生成**: ReportLab

## 项目结构

```
chen-study/
├── backend/                 # Django后端
│   ├── math_generator/      # Django项目配置
│   ├── generator/           # 题目生成应用
│   │   ├── question_generator.py  # 题目生成逻辑
│   │   ├── pdf_generator.py        # PDF生成逻辑
│   │   ├── views.py                # API视图
│   │   └── urls.py                 # URL路由
│   ├── requirements.txt     # Python依赖
│   └── manage.py
├── frontend/                # React前端
│   ├── src/
│   │   ├── App.js          # 主组件
│   │   ├── App.css         # 样式
│   │   └── index.js        # 入口文件
│   ├── public/
│   └── package.json        # Node依赖
├── start.sh                 # 一键启动脚本（同时启动前后端）
├── stop.sh                  # 停止所有服务脚本
├── start_backend.sh         # 单独启动后端脚本
├── start_frontend.sh        # 单独启动前端脚本
└── README.md
```

## 安装和运行

### 方式一：一键启动（推荐）

使用提供的启动脚本同时启动前后端：

```bash
# 启动所有服务
./start.sh

# 停止所有服务（在另一个终端运行）
./stop.sh
```

脚本会自动：
- 检查并创建虚拟环境
- 安装依赖（如果未安装）
- 运行数据库迁移
- 启动后端服务（http://localhost:8000）
- 启动前端服务（http://localhost:3000）
- 实时显示日志

按 `Ctrl+C` 可以停止所有服务。

### 方式二：分别启动

如果需要分别启动前后端：

#### 1. 后端设置

```bash
# 启动后端
./start_backend.sh

# 或手动启动
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

后端服务将在 `http://localhost:8000` 运行

#### 2. 前端设置

```bash
# 启动前端（新终端）
./start_frontend.sh

# 或手动启动
cd frontend
npm install
npm start
```

前端应用将在 `http://localhost:3000` 运行

## API接口

### 生成预览
- **URL**: `/api/generate-preview/`
- **方法**: POST
- **参数**:
  ```json
  {
    "num_pages": 2,           // 页数
    "max_value": 20,          // 最大数值
    "operations": ["addition", "subtraction", "multiplication", "division"],
    "fill_type": "result"     // "result" 或 "operand"
  }
  ```
- **返回**: HTML预览内容

### 生成PDF
- **URL**: `/api/generate-pdf/`
- **方法**: POST
- **参数**: 同生成预览
- **返回**: PDF文件下载

## 使用说明

1. 打开前端应用 `http://localhost:3000`
2. 设置参数：
   - **页数 (N)**: 要生成的页数（1-50）
   - **最大数值 (M)**: 题目中出现的最大数值（1-100）
   - **运算类型**: 选择要包含的运算
     - 基础运算：加法、减法、乘法、除法
     - 混合运算：加乘、加除、减乘、减除（遵循先乘除后加减的运算顺序）
   - **题目类型**: 选择填写结果或填写中间值
3. 点击"生成预览"查看效果
4. 确认无误后点击"下载PDF"保存文件

## 注意事项

- 乘法和除法是表内运算（1-9的乘法表）
- 每页固定生成20道题目，排列为4列5行
- PDF格式为A4纸张，适合打印
- 确保后端服务运行在前端可以访问的地址

## 开发说明

### 添加新的运算类型

在 `backend/generator/question_generator.py` 中添加新的生成方法，并在 `generate_questions` 方法中调用。

### 修改PDF布局

编辑 `backend/generator/pdf_generator.py` 中的 `generate_pdf` 方法，调整布局参数。

### 自定义样式

修改 `frontend/src/App.css` 来自定义前端样式。

## 许可证

MIT License
