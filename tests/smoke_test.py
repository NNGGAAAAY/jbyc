import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_anesthesia.db"

from fastapi.testclient import TestClient

from app.main import app


def main():
    with TestClient(app) as client:
        login = client.post("/auth/login", json={"username": "admin", "password": "Admin@123"})
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        models = client.get("/models")
        assert models.status_code == 200
        imported = client.post(
            "/datasets/import-path",
            json={"path": r"E:\Desktop\Anesthesia_Dataset.csv", "name": "smoke-test"},
        )
        assert imported.status_code == 200, imported.text
        dataset_id = imported.json()["id"]
        test_parameters = {
            "xgb": {"n_estimators": 10, "max_depth": 2},
            "rf": {"n_estimators": 20, "max_depth": 3},
            "svm": {},
            "catboost": {"iterations": 10, "depth": 3},
            "dt": {"max_depth": 3},
            "ann": {"epochs": 5},
            "rnn": {"epochs": 5},
            "knn": {"n_neighbors": 5},
        }
        results = {}
        for model_name, parameters in test_parameters.items():
            trained = client.post(
                "/train/sync",
                json={"dataset_id": dataset_id, "model_name": model_name, "parameters": parameters},
            )
            assert trained.status_code == 200, f"{model_name}: {trained.text}"
            run = client.get(f"/runs/{trained.json()['run_id']}")
            assert run.status_code == 200
            body = run.json()
            assert body["train_confusion_matrix"]
            assert body["test_roc"]["fpr"]
            assert body["shap"]["mean_abs_shap"]
            results[model_name] = trained.json()["test_metrics"]
        analysis = client.get(f"/datasets/{dataset_id}/analysis", headers=headers)
        assert analysis.status_code == 200, analysis.text
        assert analysis.json()["numeric_summary"]
        queued = client.post("/train", headers=headers, json={"dataset_id": dataset_id, "model_name": "dt", "parameters": {"max_depth": 2}})
        assert queued.status_code == 200, queued.text
        tasks = client.get("/tasks", headers=headers)
        assert tasks.status_code == 200 and tasks.json()
        print({"models": models.json(), "test_metrics": results})


if __name__ == "__main__":
    main()
