# Anesthesia ML Service

基于 FastAPI 的术前并发症二分类训练服务，支持 `xgb`、`rf`、`svm`、`catboost`、`dt`、`ann`、`rnn`、`knn`。

## 1. 创建数据库

```sql
CREATE DATABASE anesthesia_ml CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

PowerShell 中设置连接并启动：

```powershell
conda activate pytorch
pip install -r requirements.txt
$env:DATABASE_URL='mysql+pymysql://root:你的密码@127.0.0.1:3306/anesthesia_ml?charset=utf8mb4'
uvicorn app.main:app --reload
```

打开 `http://127.0.0.1:8000/docs` 操作接口。

## Vue 3 前端

```powershell
cd frontend
npm install
npm run dev
```

浏览器访问 `http://127.0.0.1:5173`。如后端地址不同，复制 `frontend/.env.example` 为 `.env` 并修改 `VITE_API_BASE_URL`。

初始管理员账号为 `admin`，密码为 `Admin@123`。正式使用前请通过环境变量 `ADMIN_PASSWORD` 修改初始密码。

系统现已采用异步训练流程：`POST /train` 仅创建队列任务，后台工作线程按照优先级从高到低、同优先级按创建时间从早到晚执行。前端“训练队列”页面每 2 秒刷新任务状态和训练日志。

数据集导入后，可在数据集列表进入“数据分析”，查看数据质量概览、字段缺失、分类分布、数值统计与字段字典。

## 2. 使用顺序

1. `POST /datasets/import-path` 导入本机 CSV，例如 `E:\\Desktop\\Anesthesia_Dataset.csv`；也可用 `/datasets/upload` 上传。
2. `GET /models` 查看模型名称。
3. `POST /train` 选择数据集和模型训练。
4. `GET /runs/{run_id}` 查看训练/测试指标、混淆矩阵、ROC 原始数据和 SHAP 结果。

模型及预处理器保存在 `artifacts/models`，ROC、混淆矩阵及 SHAP JSON 保存在 `artifacts/results`，同样会记录进 MySQL。

默认只使用术前字段：`Age`、`Gender`、`BMI`、`SurgeryType`、`SurgeryDuration`、`AnesthesiaType`、`PreoperativeNotes`。`PostoperativeNotes`、`PainLevel`、`Complications` 会被排除，以避免标签泄漏。
