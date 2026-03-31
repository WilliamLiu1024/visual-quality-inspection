# 钢板视觉缺陷检测项目

基于 `FastAPI + SQLite + YOLO26` 的前后端一体化项目，用于钢板表面缺陷检测。项目提供一个轻量 Web 界面，支持测试图片识别、视频流检测、异常状态展示以及历史记录查询。

## 功能概览

- 使用 YOLO26 模型统一输出 `defect` / `normal` 两类结果
- 支持测试图片快速验证模型效果
- 支持 USB 摄像头、RTSP 或本地测试目录作为视频源
- 实时展示当前状态、置信度、缺陷框数量与更新时间
- 自动保存异常帧，并将检测记录写入 SQLite

## 项目结构

```text
backend/
  app/                  FastAPI 服务、检测主链、数据存储与视频流逻辑
  models/               当前服务使用的模型权重
frontend/               原生 HTML/CSS/JS 前端页面
scripts/                当前保留的数据准备与训练脚本
run_steel_detection.*   本地一键启动脚本
```

## 快速启动

### 方式一：直接双击

直接运行 `run_steel_detection.bat`。

脚本会自动：

- 创建虚拟环境（若不存在）
- 安装 Web 端运行依赖
- 启动 FastAPI 服务
- 等待约 4 秒后自动打开浏览器

### 方式二：命令行启动

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
$env:DETECTOR_NAME = 'yolo26'
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

启动后访问：`http://127.0.0.1:8000/`

## 模型与数据说明

- 当前服务主链只保留 `yolo26` 这一条实际使用的检测链路
- 推理权重默认位于 `backend/models/yolo26-steel.pt`
- 运行期数据目录在 `backend/app/config.py` 中配置，当前默认指向 `D:\05Data\visual-quality-inspection\data`
- 如果模型权重不存在，前端仍可打开，但健康检查会显示模型未就绪

## 训练相关脚本

仓库当前保留 3 个仍在使用的训练链路脚本：

- `scripts/prepare_classification_from_current_train.py`：从当前 `train` 数据构建分类数据集
- `scripts/prepare_classification_current_balanced.py`：生成平衡后的当前分类训练集
- `scripts/train_yolo26_steel_current.py`：训练当前模型并导出到 `backend/models/yolo26-steel.pt`

历史实验脚本、未接入算法占位代码以及训练产物目录已经从仓库移除，以保持主线清晰。

## 运行注意事项

- 本机脚本按 Python 3.14 环境整理
- 如果要进行真实视频检测，需要准备可用的视频源
- SQLite、上传图片和运行缓存属于本地运行状态，不建议直接提交新的运行产物

## 当前技术栈

- Backend: FastAPI, SQLAlchemy, OpenCV
- Frontend: HTML, CSS, Vanilla JavaScript
- Model: Ultralytics YOLO
- Storage: SQLite
