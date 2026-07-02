import json
import os
import hashlib
import secrets
import shutil
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
import torch
from catboost import CatBoostClassifier
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text, create_engine, func
from sqlalchemy.orm import declarative_base, sessionmaker
from xgboost import XGBClassifier


BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
MODEL_DIR = BASE_DIR / "artifacts" / "models"
RESULT_DIR = BASE_DIR / "artifacts" / "results"
for directory in (UPLOAD_DIR, MODEL_DIR, RESULT_DIR):
    directory.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:password@127.0.0.1:3306/anesthesia_ml?charset=utf8mb4",
)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class DatasetRecord(Base):
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True)
    owner_user_id = Column(Integer)
    name = Column(String(255), nullable=False)
    dataset_type = Column(String(30), default="training", nullable=False)
    source_type = Column(String(30), default="upload", nullable=False)
    original_filename = Column(String(255))
    file_size = Column(Integer)
    file_path = Column(String(1000), nullable=False)
    row_count = Column(Integer, nullable=False)
    columns_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.now)


class TrainingRun(Base):
    __tablename__ = "training_runs"
    id = Column(String(36), primary_key=True)
    dataset_id = Column(Integer, nullable=False)
    model_name = Column(String(30), nullable=False)
    version_no = Column(Integer, default=1, nullable=False)
    target_column = Column(String(100), default="Outcome")
    test_size = Column(Float, default=0.2)
    random_state = Column(Integer, default=42)
    status = Column(String(30), nullable=False)
    parameters = Column(JSON)
    train_metrics = Column(JSON)
    test_metrics = Column(JSON)
    train_confusion_matrix = Column(JSON)
    test_confusion_matrix = Column(JSON)
    train_roc = Column(JSON)
    test_roc = Column(JSON)
    shap_result = Column(JSON)
    model_path = Column(String(1000))
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(120), nullable=False)
    created_at = Column(DateTime, default=datetime.now)


class AccessToken(Base):
    __tablename__ = "access_tokens"
    token = Column(String(64), primary_key=True)
    user_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.now)


class TrainingTask(Base):
    __tablename__ = "training_tasks"
    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, nullable=False)
    dataset_id = Column(Integer, nullable=False)
    model_name = Column(String(30), nullable=False)
    request_json = Column(JSON, nullable=False)
    priority = Column(Integer, default=0, nullable=False)
    status = Column(String(30), default="queued", nullable=False)
    queue_position = Column(Integer)
    run_id = Column(String(36))
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)


class TrainingLog(Base):
    __tablename__ = "training_logs"
    id = Column(Integer, primary_key=True)
    task_id = Column(String(36), nullable=False, index=True)
    level = Column(String(20), default="info")
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)


class InferenceRun(Base):
    __tablename__ = "inference_runs"
    id = Column(String(36), primary_key=True)
    training_run_id = Column(String(36), nullable=False)
    dataset_id = Column(Integer, nullable=False)
    threshold = Column(Float, default=0.5, nullable=False)
    output_name = Column(String(255), nullable=False)
    output_file_path = Column(String(1000), nullable=False)
    row_count = Column(Integer, nullable=False)
    summary_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.now)


class ImportPathRequest(BaseModel):
    path: str
    name: str | None = None
    dataset_type: str = "training"


class TrainRequest(BaseModel):
    dataset_id: int
    model_name: str
    target_column: str = "Outcome"
    test_size: float = 0.2
    random_state: int = 42
    parameters: dict = Field(default_factory=dict)


class LoginRequest(BaseModel):
    username: str
    password: str


class QueueTrainRequest(TrainRequest):
    priority: int = 0


class PriorityRequest(BaseModel):
    priority: int


class InferenceRequest(BaseModel):
    training_run_id: str
    dataset_id: int
    threshold: float = 0.5
    output_name: str | None = None


class DatasetUpdateRequest(BaseModel):
    name: str | None = None
    dataset_type: str | None = None


class TorchBinaryModel(torch.nn.Module):
    def __init__(self, input_size: int):
        super().__init__()
        self.layers = torch.nn.Sequential(
            torch.nn.Linear(input_size, 64),
            torch.nn.ReLU(),
            torch.nn.Linear(64, 32),
            torch.nn.ReLU(),
            torch.nn.Linear(32, 1),
        )

    def forward(self, x):
        return self.layers(x).squeeze(1)


class TorchRNNModel(torch.nn.Module):
    def __init__(self, input_size: int, hidden_size: int = 32):
        super().__init__()
        self.hidden_size = hidden_size
        self.rnn = torch.nn.RNN(1, hidden_size, batch_first=True)
        self.output = torch.nn.Linear(hidden_size, 1)

    def forward(self, x):
        sequence = x.unsqueeze(-1)
        output, _ = self.rnn(sequence)
        return self.output(output[:, -1, :]).squeeze(1)


app = FastAPI(title="Anesthesia Complication ML Service", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://ojxdxcx.xyz",
        "http://www.ojxdxcx.xyz",
        "https://ojxdxcx.xyz",
        "https://www.ojxdxcx.xyz",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if not db.query(User).filter(User.username == "admin").first():
            db.add(User(username="admin", display_name="系统管理员", password_hash=hash_password(os.getenv("ADMIN_PASSWORD", "Admin@123"))))
            db.commit()
    if not any(thread.name == "training-worker" for thread in threading.enumerate()):
        threading.Thread(target=training_worker, name="training-worker", daemon=True).start()


def hash_password(password: str):
    salt = "anesthesia-ml-studio"
    return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()


def current_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "请先登录")
    token_value = authorization.removeprefix("Bearer ")
    with SessionLocal() as db:
        token = db.get(AccessToken, token_value)
        user = db.get(User, token.user_id) if token else None
        if not user:
            raise HTTPException(401, "登录状态已失效")
        return {"id": user.id, "username": user.username, "display_name": user.display_name}


def ensure_dataset_access(db, dataset_id: int, user_id: int):
    dataset = db.get(DatasetRecord, dataset_id)
    if not dataset or (dataset.owner_user_id is not None and dataset.owner_user_id != user_id):
        raise HTTPException(404, "数据集不存在")
    return dataset


def dataset_payload(dataset: DatasetRecord):
    return {
        "id": dataset.id,
        "name": dataset.name,
        "rows": dataset.row_count,
        "columns": dataset.columns_json,
        "dataset_type": dataset.dataset_type,
        "source_type": dataset.source_type,
        "original_filename": dataset.original_filename,
        "file_size": dataset.file_size,
        "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
    }


def run_payload(run: TrainingRun, dataset_name: str | None = None):
    return {
        "id": run.id,
        "dataset_id": run.dataset_id,
        "dataset_name": dataset_name,
        "model_name": run.model_name,
        "version_no": run.version_no,
        "target_column": run.target_column,
        "test_size": run.test_size,
        "random_state": run.random_state,
        "status": run.status,
        "parameters": run.parameters,
        "test_metrics": run.test_metrics,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


def add_log(task_id: str, message: str, level: str = "info"):
    with SessionLocal() as db:
        db.add(TrainingLog(task_id=task_id, message=message, level=level))
        db.commit()


def training_worker():
    while True:
        task_id = None
        with SessionLocal() as db:
            task = db.query(TrainingTask).filter(TrainingTask.status == "queued").order_by(TrainingTask.priority.desc(), TrainingTask.created_at.asc()).first()
            if task:
                task.status = "running"
                task.started_at = datetime.now()
                task_id = task.id
                request_data = task.request_json
                db.commit()
        if not task_id:
            time.sleep(1)
            continue
        try:
            add_log(task_id, "任务已离开队列，开始读取数据集")
            add_log(task_id, "正在执行特征预处理与分层数据划分")
            result = train_sync(TrainRequest(**request_data))
            add_log(task_id, "模型训练完成，评价指标已计算")
            add_log(task_id, "ROC、混淆矩阵与 SHAP 解释已保存")
            with SessionLocal() as db:
                task = db.get(TrainingTask, task_id)
                task.status = "completed"
                task.run_id = result["run_id"]
                task.finished_at = datetime.now()
                db.commit()
        except Exception as error:
            add_log(task_id, f"训练失败：{error}", "error")
            with SessionLocal() as db:
                task = db.get(TrainingTask, task_id)
                task.status = "failed"
                task.error_message = str(error)
                task.finished_at = datetime.now()
                db.commit()


def save_dataset(source_path: Path, name: str, user_id: int | None = None, source_type: str = "upload", original_filename: str | None = None, dataset_type: str = "training"):
    data = pd.read_csv(source_path)
    destination = UPLOAD_DIR / f"{uuid.uuid4().hex}_{source_path.name}"
    shutil.copy2(source_path, destination)
    with SessionLocal() as db:
        record = DatasetRecord(
            owner_user_id=user_id,
            name=name,
            dataset_type=dataset_type,
            source_type=source_type,
            original_filename=original_filename or source_path.name,
            file_size=destination.stat().st_size,
            file_path=str(destination),
            row_count=len(data),
            columns_json=list(data.columns),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return {
            "id": record.id,
            "name": record.name,
            "rows": record.row_count,
            "columns": record.columns_json,
            "dataset_type": record.dataset_type,
            "source_type": record.source_type,
            "original_filename": record.original_filename,
            "file_size": record.file_size,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }


@app.get("/")
def root():
    return {"message": "Anesthesia ML service is running", "docs": "/docs"}


@app.get("/models")
def model_options():
    return {"models": ["xgb", "rf", "svm", "catboost", "dt", "ann", "rnn", "knn"]}


@app.post("/datasets/import-path")
def import_dataset_path(request: ImportPathRequest, user=Depends(current_user)):
    source = Path(request.path)
    if not source.exists() or source.suffix.lower() != ".csv":
        raise HTTPException(400, "CSV 文件不存在")
    return save_dataset(source, request.name or source.stem, user_id=user["id"], source_type="path_import", original_filename=source.name, dataset_type=request.dataset_type)


@app.post("/datasets/upload")
def upload_dataset(file: UploadFile = File(...), dataset_type: str = Form("training"), user=Depends(current_user)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "只支持 CSV 文件")
    temp_path = UPLOAD_DIR / f"temp_{uuid.uuid4().hex}.csv"
    with temp_path.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    result = save_dataset(temp_path, Path(file.filename).stem, user_id=user["id"], source_type="browser_upload", original_filename=file.filename, dataset_type=dataset_type)
    temp_path.unlink()
    return result


@app.get("/datasets")
def list_datasets(user=Depends(current_user)):
    with SessionLocal() as db:
        rows = db.query(DatasetRecord).filter((DatasetRecord.owner_user_id == None) | (DatasetRecord.owner_user_id == user["id"])).order_by(DatasetRecord.id.desc()).all()
        return [dataset_payload(item) for item in rows]


@app.patch("/datasets/{dataset_id}")
def update_dataset(dataset_id: int, request: DatasetUpdateRequest, user=Depends(current_user)):
    with SessionLocal() as db:
        dataset = ensure_dataset_access(db, dataset_id, user["id"])
        if request.name is not None and request.name.strip():
            dataset.name = request.name.strip()
        if request.dataset_type is not None and request.dataset_type.strip():
            dataset.dataset_type = request.dataset_type.strip()
        db.commit()
        db.refresh(dataset)
        return {
            "id": dataset.id,
            "name": dataset.name,
            "dataset_type": dataset.dataset_type,
            "source_type": dataset.source_type,
            "original_filename": dataset.original_filename,
        }


@app.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: int, user=Depends(current_user)):
    with SessionLocal() as db:
        dataset = ensure_dataset_access(db, dataset_id, user["id"])
        file_path = Path(dataset.file_path)
        db.delete(dataset)
        db.commit()
    if file_path.exists():
        file_path.unlink()
    return {"message": "数据集已删除"}


def build_feature_frame(data: pd.DataFrame):
    allowed = [
        "Age", "Gender", "BMI", "SurgeryType", "SurgeryDuration",
        "AnesthesiaType", "PreoperativeNotes",
    ]
    features = [column for column in allowed if column in data.columns]
    frame = data[features].copy()
    if "SurgeryDuration" in frame:
        frame["SurgeryDuration"] = frame["SurgeryDuration"].astype(str).str.extract(r"(\d+)")[0].astype(float)
    return frame


def prepare_data(data: pd.DataFrame, target_column: str):
    if target_column not in data.columns:
        raise ValueError(f"缺少目标列 {target_column}")
    frame = build_feature_frame(data)
    y = data[target_column].astype(int)
    numeric = frame.select_dtypes(include=np.number).columns.tolist()
    categorical = [column for column in frame.columns if column not in numeric]
    preprocessor = ColumnTransformer([
        ("numeric", Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]), numeric),
        ("categorical", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]), categorical),
    ])
    return frame, y, preprocessor


def make_model(name: str, parameters: dict):
    defaults = {
        "xgb": XGBClassifier(n_estimators=150, max_depth=4, learning_rate=0.05, eval_metric="logloss", random_state=42),
        "rf": RandomForestClassifier(n_estimators=200, random_state=42),
        "svm": SVC(probability=True, random_state=42),
        "catboost": CatBoostClassifier(iterations=150, depth=5, learning_rate=0.05, verbose=False, random_seed=42),
        "dt": DecisionTreeClassifier(max_depth=5, random_state=42),
        "knn": KNeighborsClassifier(n_neighbors=5),
    }
    if name not in defaults:
        raise ValueError("传统模型名称不正确")
    model = defaults[name]
    if parameters:
        model.set_params(**parameters)
    return model


def train_torch(name, x_train, y_train, parameters):
    torch.manual_seed(42)
    hidden_size = int(parameters.get("hidden_size", 32))
    model = TorchBinaryModel(x_train.shape[1]) if name == "ann" else TorchRNNModel(x_train.shape[1], hidden_size=hidden_size)
    epochs = int(parameters.get("epochs", 100))
    learning_rate = float(parameters.get("learning_rate", 0.001))
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    loss_function = torch.nn.BCEWithLogitsLoss()
    x_tensor = torch.tensor(x_train, dtype=torch.float32)
    y_tensor = torch.tensor(y_train.to_numpy(), dtype=torch.float32)
    model.train()
    for _ in range(epochs):
        optimizer.zero_grad()
        loss = loss_function(model(x_tensor), y_tensor)
        loss.backward()
        optimizer.step()
    return model


def torch_probability(model, values):
    model.eval()
    with torch.no_grad():
        logits = model(torch.tensor(values, dtype=torch.float32))
        return torch.sigmoid(logits).numpy()


def evaluate(y_true, probability):
    prediction = (probability >= 0.5).astype(int)
    fpr, tpr, thresholds = roc_curve(y_true, probability)
    metrics = {
        "accuracy": float(accuracy_score(y_true, prediction)),
        "precision": float(precision_score(y_true, prediction, zero_division=0)),
        "recall": float(recall_score(y_true, prediction, zero_division=0)),
        "f1": float(f1_score(y_true, prediction, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, probability)),
    }
    matrix = confusion_matrix(y_true, prediction, labels=[0, 1]).tolist()
    threshold_values = [float(value) if np.isfinite(value) else None for value in thresholds]
    roc = {"fpr": fpr.tolist(), "tpr": tpr.tolist(), "thresholds": threshold_values}
    return metrics, matrix, roc


def calculate_shap(model_name, model, x_train, x_test, feature_names):
    sample = x_test[: min(50, len(x_test))]
    background = x_train[: min(50, len(x_train))]
    if model_name in {"rf", "catboost", "dt"}:
        explainer = shap.TreeExplainer(model)
        values = explainer.shap_values(sample)
        if isinstance(values, list):
            values = values[-1]
        if np.asarray(values).ndim == 3:
            values = np.asarray(values)[:, :, -1]
    else:
        prediction_function = lambda value: (
            torch_probability(model, value) if model_name in {"ann", "rnn"} else model.predict_proba(value)[:, 1]
        )
        explainer = shap.KernelExplainer(prediction_function, background)
        values = explainer.shap_values(sample, nsamples=100)
    values = np.asarray(values)
    importance = np.mean(np.abs(values), axis=0)
    return {
        "feature_names": list(feature_names),
        "mean_abs_shap": importance.astype(float).tolist(),
        "sample_values": values.astype(float).tolist(),
    }


def load_run_model(run: TrainingRun):
    if run.model_name in {"ann", "rnn"}:
        payload = torch.load(run.model_path, map_location="cpu")
        if run.model_name == "ann":
            model = TorchBinaryModel(payload["input_size"])
        else:
            model = TorchRNNModel(payload["input_size"], hidden_size=payload.get("hidden_size", 32))
        model.load_state_dict(payload["state_dict"])
        preprocessor = joblib.load(MODEL_DIR / f"{run.id}_preprocessor.joblib")
        return preprocessor, model
    bundle = joblib.load(run.model_path)
    return bundle["preprocessor"], bundle["model"]


@app.post("/train/sync")
def train_sync(request: TrainRequest):
    if request.model_name not in {"xgb", "rf", "svm", "catboost", "dt", "ann", "rnn", "knn"}:
        raise HTTPException(400, "不支持的模型")
    run_id = str(uuid.uuid4())
    with SessionLocal() as db:
        dataset = db.get(DatasetRecord, request.dataset_id)
        if not dataset:
            raise HTTPException(404, "数据集不存在")
        version_no = (db.query(func.max(TrainingRun.version_no)).filter(TrainingRun.model_name == request.model_name).scalar() or 0) + 1
        run = TrainingRun(
            id=run_id, dataset_id=dataset.id, model_name=request.model_name,
            version_no=version_no,
            target_column=request.target_column, test_size=request.test_size,
            random_state=request.random_state, status="training", parameters=request.parameters,
        )
        db.add(run)
        db.commit()
        try:
            data = pd.read_csv(dataset.file_path)
            x, y, preprocessor = prepare_data(data, request.target_column)
            x_train, x_test, y_train, y_test = train_test_split(
                x, y, test_size=request.test_size, random_state=request.random_state, stratify=y,
            )
            train_values = preprocessor.fit_transform(x_train).astype(np.float32)
            test_values = preprocessor.transform(x_test).astype(np.float32)
            feature_names = preprocessor.get_feature_names_out().tolist()

            if request.model_name in {"ann", "rnn"}:
                model = train_torch(request.model_name, train_values, y_train, request.parameters)
                train_probability = torch_probability(model, train_values)
                test_probability = torch_probability(model, test_values)
                model_path = MODEL_DIR / f"{run_id}.pt"
                torch.save({
                    "state_dict": model.state_dict(),
                    "input_size": train_values.shape[1],
                    "model_name": request.model_name,
                    "hidden_size": getattr(model, "hidden_size", None),
                }, model_path)
                joblib.dump(preprocessor, MODEL_DIR / f"{run_id}_preprocessor.joblib")
            else:
                model = make_model(request.model_name, request.parameters)
                model.fit(train_values, y_train)
                train_probability = model.predict_proba(train_values)[:, 1]
                test_probability = model.predict_proba(test_values)[:, 1]
                model_path = MODEL_DIR / f"{run_id}.joblib"
                joblib.dump({"preprocessor": preprocessor, "model": model}, model_path)

            train_metrics, train_matrix, train_roc = evaluate(y_train, train_probability)
            test_metrics, test_matrix, test_roc = evaluate(y_test, test_probability)
            shap_result = calculate_shap(request.model_name, model, train_values, test_values, feature_names)

            result_path = RESULT_DIR / f"{run_id}.json"
            result_data = {
                "train_metrics": train_metrics, "test_metrics": test_metrics,
                "train_confusion_matrix": train_matrix, "test_confusion_matrix": test_matrix,
                "train_roc": train_roc, "test_roc": test_roc, "shap": shap_result,
            }
            result_path.write_text(json.dumps(result_data, ensure_ascii=False), encoding="utf-8")

            run.status = "completed"
            run.train_metrics = train_metrics
            run.test_metrics = test_metrics
            run.train_confusion_matrix = train_matrix
            run.test_confusion_matrix = test_matrix
            run.train_roc = train_roc
            run.test_roc = test_roc
            run.shap_result = shap_result
            run.model_path = str(model_path)
            db.commit()
            return {"run_id": run_id, "status": "completed", "train_metrics": train_metrics, "test_metrics": test_metrics}
        except Exception as error:
            run.status = "failed"
            run.error_message = str(error)
            db.commit()
            raise HTTPException(500, str(error))


@app.get("/runs")
def list_runs():
    with SessionLocal() as db:
        rows = db.query(TrainingRun).order_by(TrainingRun.created_at.desc()).all()
        dataset_names = {item.id: item.name for item in db.query(DatasetRecord).all()}
        return [run_payload(item, dataset_names.get(item.dataset_id)) for item in rows]


@app.get("/model-versions")
def model_versions():
    with SessionLocal() as db:
        runs = db.query(TrainingRun).order_by(TrainingRun.model_name.asc(), TrainingRun.version_no.desc()).all()
        dataset_names = {item.id: item.name for item in db.query(DatasetRecord).all()}
        grouped = {}
        for run in runs:
            model_group = grouped.setdefault(run.model_name, {
                "model_name": run.model_name,
                "total_versions": 0,
                "completed_versions": 0,
                "latest_version_no": 0,
                "best_auc": None,
                "versions": [],
            })
            model_group["total_versions"] += 1
            model_group["latest_version_no"] = max(model_group["latest_version_no"], run.version_no or 0)
            auc = (run.test_metrics or {}).get("roc_auc")
            if auc is not None:
                model_group["best_auc"] = auc if model_group["best_auc"] is None else max(model_group["best_auc"], auc)
            if run.status == "completed":
                model_group["completed_versions"] += 1
            model_group["versions"].append(run_payload(run, dataset_names.get(run.dataset_id)))
        return list(grouped.values())


@app.get("/runs/{run_id}")
def get_run(run_id: str):
    with SessionLocal() as db:
        run = db.get(TrainingRun, run_id)
        if not run:
            raise HTTPException(404, "训练记录不存在")
        return {
            "id": run.id, "dataset_id": run.dataset_id, "model_name": run.model_name, "version_no": run.version_no,
            "target_column": run.target_column, "test_size": run.test_size, "random_state": run.random_state,
            "status": run.status, "parameters": run.parameters,
            "train_metrics": run.train_metrics, "test_metrics": run.test_metrics,
            "train_confusion_matrix": run.train_confusion_matrix,
            "test_confusion_matrix": run.test_confusion_matrix,
            "train_roc": run.train_roc, "test_roc": run.test_roc,
            "shap": run.shap_result, "model_path": run.model_path,
            "error_message": run.error_message,
        }


@app.post("/auth/login")
def login(request: LoginRequest):
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == request.username).first()
        if not user or user.password_hash != hash_password(request.password):
            raise HTTPException(401, "用户名或密码错误")
        token_value = secrets.token_hex(32)
        db.add(AccessToken(token=token_value, user_id=user.id))
        db.commit()
        return {"token": token_value, "user": {"id": user.id, "username": user.username, "display_name": user.display_name}}


@app.get("/auth/me")
def me(user=Depends(current_user)):
    return user


@app.post("/auth/logout")
def logout(authorization: str | None = Header(default=None), user=Depends(current_user)):
    with SessionLocal() as db:
        db.query(AccessToken).filter(AccessToken.token == authorization.removeprefix("Bearer ")).delete()
        db.commit()
    return {"message": "已退出登录"}


@app.get("/datasets/{dataset_id}/analysis")
def dataset_analysis(dataset_id: int, user=Depends(current_user)):
    with SessionLocal() as db:
        dataset = ensure_dataset_access(db, dataset_id, user["id"])
        data = pd.read_csv(dataset.file_path)
    numeric_columns = data.select_dtypes(include=np.number).columns.tolist()
    categorical_columns = [column for column in data.columns if column not in numeric_columns]
    numeric_summary = []
    for column in numeric_columns:
        series = data[column].dropna()
        numeric_summary.append({
            "column": column, "mean": float(series.mean()), "median": float(series.median()),
            "min": float(series.min()), "max": float(series.max()), "std": float(series.std()) if len(series) > 1 else 0,
        })
    distributions = {}
    for column in categorical_columns[:8]:
        counts = data[column].fillna("缺失").astype(str).value_counts().head(12)
        distributions[column] = [{"label": label, "value": int(value)} for label, value in counts.items()]
    if "Outcome" in data.columns:
        counts = data["Outcome"].fillna("缺失").astype(str).value_counts()
        distributions["Outcome"] = [{"label": label, "value": int(value)} for label, value in counts.items()]
    numeric_histograms = {}
    numeric_boxplots = {}
    for column in numeric_columns[:8]:
        series = data[column].dropna().astype(float)
        if series.empty:
            continue
        bin_count = min(12, max(5, int(np.sqrt(len(series)))))
        counts, edges = np.histogram(series, bins=bin_count)
        numeric_histograms[column] = [{
            "left": float(edges[index]),
            "right": float(edges[index + 1]),
            "count": int(counts[index]),
        } for index in range(len(counts))]
        q0, q1, q2, q3, q4 = series.quantile([0, 0.25, 0.5, 0.75, 1]).tolist()
        numeric_boxplots[column] = [float(q0), float(q1), float(q2), float(q3), float(q4)]
    correlation = {"columns": [], "matrix": []}
    correlation_pairs = []
    if len(numeric_columns) >= 2:
        corr_columns = numeric_columns[:10]
        corr_frame = data[corr_columns].corr(method="pearson").fillna(0)
        correlation = {
            "columns": corr_columns,
            "matrix": [
                [x_index, y_index, float(corr_frame.iloc[y_index, x_index])]
                for y_index in range(len(corr_columns))
                for x_index in range(len(corr_columns))
            ],
        }
        pair_items = []
        for left_index in range(len(corr_columns)):
            for right_index in range(left_index + 1, len(corr_columns)):
                pair_items.append({
                    "pair": f"{corr_columns[left_index]} vs {corr_columns[right_index]}",
                    "value": float(corr_frame.iloc[right_index, left_index]),
                    "abs_value": float(abs(corr_frame.iloc[right_index, left_index])),
                })
        correlation_pairs = sorted(pair_items, key=lambda item: item["abs_value"], reverse=True)[:12]
    row_missing_counts = data.isna().sum(axis=1).value_counts().sort_index()
    row_missing_histogram = [{"missing": int(key), "count": int(value)} for key, value in row_missing_counts.items()]
    numeric_outlier_rates = []
    for column in numeric_columns[:12]:
        series = data[column].dropna().astype(float)
        if series.empty:
            continue
        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outlier_count = int(((series < lower) | (series > upper)).sum()) if iqr > 0 else 0
        numeric_outlier_rates.append({
            "column": column,
            "count": outlier_count,
            "rate": float(outlier_count / len(series)) if len(series) else 0.0,
        })
    return {
        "dataset_id": dataset_id, "name": dataset.name, "rows": len(data), "columns": len(data.columns),
        "dataset_type": dataset.dataset_type,
        "source_type": dataset.source_type, "original_filename": dataset.original_filename,
        "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
        "duplicate_rows": int(data.duplicated().sum()),
        "missing_total": int(data.isna().sum().sum()),
        "column_types": [{"column": column, "type": "数值" if column in numeric_columns else "类别/文本", "missing": int(data[column].isna().sum()), "unique": int(data[column].nunique(dropna=True))} for column in data.columns],
        "numeric_summary": numeric_summary, "distributions": distributions,
        "numeric_histograms": numeric_histograms, "numeric_boxplots": numeric_boxplots,
        "correlation": correlation,
        "correlation_pairs": correlation_pairs,
        "row_missing_histogram": row_missing_histogram,
        "numeric_outlier_rates": numeric_outlier_rates,
    }


@app.post("/train")
def enqueue_training(request: QueueTrainRequest, user=Depends(current_user)):
    if request.model_name not in {"xgb", "rf", "svm", "catboost", "dt", "ann", "rnn", "knn"}:
        raise HTTPException(400, "不支持的模型")
    task_id = str(uuid.uuid4())
    request_data = request.model_dump(exclude={"priority"})
    with SessionLocal() as db:
        ensure_dataset_access(db, request.dataset_id, user["id"])
        db.add(TrainingTask(id=task_id, user_id=user["id"], dataset_id=request.dataset_id, model_name=request.model_name, request_json=request_data, priority=request.priority, status="queued"))
        db.add(TrainingLog(task_id=task_id, message="训练任务已创建，等待队列调度"))
        db.commit()
    return {"task_id": task_id, "status": "queued", "message": "训练任务已加入队列"}


def task_payload(task, position=None):
    return {
        "id": task.id, "dataset_id": task.dataset_id, "model_name": task.model_name,
        "priority": task.priority, "status": task.status, "queue_position": position,
        "run_id": task.run_id, "error_message": task.error_message,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    }


@app.get("/tasks")
def list_tasks(user=Depends(current_user)):
    with SessionLocal() as db:
        queued = db.query(TrainingTask).filter(TrainingTask.status == "queued").order_by(TrainingTask.priority.desc(), TrainingTask.created_at.asc()).all()
        positions = {task.id: index + 1 for index, task in enumerate(queued)}
        tasks = db.query(TrainingTask).order_by(TrainingTask.created_at.desc()).all()
        return [task_payload(task, positions.get(task.id)) for task in tasks]


@app.get("/tasks/{task_id}")
def get_task(task_id: str, user=Depends(current_user)):
    with SessionLocal() as db:
        task = db.get(TrainingTask, task_id)
        if not task:
            raise HTTPException(404, "训练任务不存在")
        queued = db.query(TrainingTask).filter(TrainingTask.status == "queued").order_by(TrainingTask.priority.desc(), TrainingTask.created_at.asc()).all()
        positions = {item.id: index + 1 for index, item in enumerate(queued)}
        return task_payload(task, positions.get(task.id))


@app.patch("/tasks/{task_id}/priority")
def change_priority(task_id: str, request: PriorityRequest, user=Depends(current_user)):
    with SessionLocal() as db:
        task = db.get(TrainingTask, task_id)
        if not task or task.status != "queued":
            raise HTTPException(400, "只能调整等待中任务的优先级")
        task.priority = request.priority
        db.add(TrainingLog(task_id=task_id, message=f"队列优先级调整为 {request.priority}"))
        db.commit()
    return {"message": "优先级已更新"}


@app.get("/tasks/{task_id}/logs")
def task_logs(task_id: str, user=Depends(current_user)):
    with SessionLocal() as db:
        logs = db.query(TrainingLog).filter(TrainingLog.task_id == task_id).order_by(TrainingLog.id.asc()).all()
        return [{"id": log.id, "level": log.level, "message": log.message, "created_at": log.created_at.isoformat()} for log in logs]


@app.get("/inference/models")
def inference_models(user=Depends(current_user)):
    with SessionLocal() as db:
        runs = db.query(TrainingRun).filter(TrainingRun.status == "completed").order_by(TrainingRun.created_at.desc()).all()
        dataset_names = {item.id: item.name for item in db.query(DatasetRecord).all()}
        return [{
            "id": run.id,
            "model_name": run.model_name,
            "version_no": run.version_no,
            "dataset_id": run.dataset_id,
            "dataset_name": dataset_names.get(run.dataset_id),
            "target_column": run.target_column,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "test_metrics": run.test_metrics,
        } for run in runs]


@app.post("/inference/run")
def inference_run(request: InferenceRequest, user=Depends(current_user)):
    with SessionLocal() as db:
        run = db.get(TrainingRun, request.training_run_id)
        if not run or run.status != "completed":
            raise HTTPException(404, "可推理的模型版本不存在")
        dataset = ensure_dataset_access(db, request.dataset_id, user["id"])
        data = pd.read_csv(dataset.file_path)
        preprocessor, model = load_run_model(run)
        required_columns = list(getattr(preprocessor, "feature_names_in_", []))
        missing_columns = [column for column in required_columns if column not in data.columns]
        if missing_columns:
            raise HTTPException(400, f"推理数据集缺少字段: {', '.join(missing_columns)}")
        frame = data[required_columns].copy()
        if "SurgeryDuration" in frame:
            frame["SurgeryDuration"] = frame["SurgeryDuration"].astype(str).str.extract(r"(\d+)")[0].astype(float)
        values = preprocessor.transform(frame).astype(np.float32)
        if run.model_name in {"ann", "rnn"}:
            probability = torch_probability(model, values)
        else:
            probability = model.predict_proba(values)[:, 1]
        prediction = (probability >= request.threshold).astype(int)
        inference_id = str(uuid.uuid4())
        output_name = request.output_name or f"{dataset.name}_预测结果_v{run.version_no}"
        result_frame = data.copy()
        result_frame["PredictionProbability"] = probability.astype(float)
        result_frame["PredictionLabel"] = prediction.astype(int)
        result_frame["ModelName"] = run.model_name
        result_frame["ModelVersion"] = run.version_no
        output_path = RESULT_DIR / f"inference_{inference_id}.csv"
        result_frame.to_csv(output_path, index=False, encoding="utf-8-sig")
        summary = {
            "rows": int(len(result_frame)),
            "positive_predictions": int(prediction.sum()),
            "negative_predictions": int((prediction == 0).sum()),
            "positive_rate": float(prediction.mean()) if len(prediction) else 0.0,
            "mean_probability": float(np.mean(probability)) if len(probability) else 0.0,
            "threshold": float(request.threshold),
        }
        db.add(InferenceRun(
            id=inference_id,
            training_run_id=run.id,
            dataset_id=dataset.id,
            threshold=request.threshold,
            output_name=output_name,
            output_file_path=str(output_path),
            row_count=len(result_frame),
            summary_json=summary,
        ))
        db.commit()
        return {
            "id": inference_id,
            "output_name": output_name,
            "training_run_id": run.id,
            "model_name": run.model_name,
            "version_no": run.version_no,
            "dataset_id": dataset.id,
            "summary": summary,
            "preview": result_frame.head(20).replace({np.nan: None}).to_dict(orient="records"),
        }


@app.get("/inference/runs")
def inference_runs(user=Depends(current_user)):
    with SessionLocal() as db:
        datasets = db.query(DatasetRecord).filter((DatasetRecord.owner_user_id == None) | (DatasetRecord.owner_user_id == user["id"])).all()
        allowed_dataset_ids = [item.id for item in datasets]
        dataset_map = {item.id: item for item in datasets}
        rows = db.query(InferenceRun).filter(InferenceRun.dataset_id.in_(allowed_dataset_ids)).order_by(InferenceRun.created_at.desc()).all()
        run_ids = [row.training_run_id for row in rows]
        run_map = {item.id: item for item in db.query(TrainingRun).filter(TrainingRun.id.in_(run_ids)).all()} if run_ids else {}
        return [{
            "id": row.id,
            "training_run_id": row.training_run_id,
            "dataset_id": row.dataset_id,
            "dataset_name": dataset_map[row.dataset_id].name if row.dataset_id in dataset_map else None,
            "dataset_type": dataset_map[row.dataset_id].dataset_type if row.dataset_id in dataset_map else None,
            "threshold": row.threshold,
            "output_name": row.output_name,
            "row_count": row.row_count,
            "summary": row.summary_json,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "model_name": run_map[row.training_run_id].model_name if row.training_run_id in run_map else None,
            "version_no": run_map[row.training_run_id].version_no if row.training_run_id in run_map else None,
            "target_column": run_map[row.training_run_id].target_column if row.training_run_id in run_map else None,
        } for row in rows]


@app.get("/inference/runs/{inference_id}")
def inference_run_detail(inference_id: str, user=Depends(current_user)):
    with SessionLocal() as db:
        row = db.get(InferenceRun, inference_id)
        if not row:
            raise HTTPException(404, "推理记录不存在")
        ensure_dataset_access(db, row.dataset_id, user["id"])
        run = db.get(TrainingRun, row.training_run_id)
        preview = []
        output_path = Path(row.output_file_path)
        if output_path.exists():
            preview = pd.read_csv(output_path).head(20).replace({np.nan: None}).to_dict(orient="records")
        return {
            "id": row.id,
            "training_run_id": row.training_run_id,
            "dataset_id": row.dataset_id,
            "threshold": row.threshold,
            "output_name": row.output_name,
            "row_count": row.row_count,
            "summary": row.summary_json,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "model_name": run.model_name if run else None,
            "version_no": run.version_no if run else None,
            "preview": preview,
        }


@app.get("/inference/runs/{inference_id}/download")
def inference_run_download(inference_id: str, user=Depends(current_user)):
    with SessionLocal() as db:
        row = db.get(InferenceRun, inference_id)
        if not row:
            raise HTTPException(404, "推理记录不存在")
        ensure_dataset_access(db, row.dataset_id, user["id"])
        output_path = Path(row.output_file_path)
    if not output_path.exists():
        raise HTTPException(404, "推理结果文件不存在")
    return FileResponse(path=output_path, filename=f"{row.output_name}.csv", media_type="text/csv")
