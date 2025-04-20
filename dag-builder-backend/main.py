from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
import os
from render_functions import TASK_RENDERERS
from render_functions.generate_id import render_generate_id
from render_functions.create_env import render_create_env
from render_functions.register_dag import render_register_dag
from render_functions.download_dataset import render_download_dataset

from dag_templates_functions.common_functions import (
    generate_execution_id_code,
    get_ml_serving_pod_info_code,
    call_api_task_code,
)

# 在 render_xxx.py 中這樣引用
from utils.safe_var import safe_python_var



app = FastAPI()

# --- Schema 定義 ---
class Task(BaseModel):
    id: str
    type: str
    config: Dict[str, str]
    upstream: List[str]

class DAGPayload(BaseModel):
    dag_name: str
    tasks: List[Task]

# ✅ 加這段就能處理 OPTIONS 請求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 或指定你的前端 URL，比如 http://localhost:3000
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




@app.post("/deploy-dag")
def deploy_dag(payload: DAGPayload):
    dag_name = payload.dag_name
    dag_file_name = f"{dag_name}.py"
    dag_file_path = f"./airflow_dags/{dag_file_name}"

    lines = [
        "from airflow import DAG",
        "from airflow.operators.python import PythonOperator",
        "from airflow.utils.dates import days_ago",
        "from datetime import datetime",
        generate_execution_id_code,
        get_ml_serving_pod_info_code,
        call_api_task_code,
        "",
        f"with DAG('{dag_name}', start_date=days_ago(1), schedule_interval=None) as dag:",
    ]

    task_blocks = []
    declared_vars = []

    for task in payload.tasks:
        if task.type == "generate_id":
            rendered = render_generate_id(task)
        elif task.type == "create_env":
            rendered = render_create_env(task)
        elif task.type == "register_dag":
            rendered = render_register_dag(task)
        elif task.type == "download_dataset":
            rendered = render_download_dataset(task)
        else:
            continue

        # 每個 rendered block 做多行縮排處理
        for line in rendered.strip().splitlines():
            task_blocks.append(f"    {line}")

        declared_vars.append(safe_python_var(task.id))

    lines.extend(task_blocks)

    # 加入依賴關係（跳過 dag_id）
    declared_vars = [safe_python_var(task.id) for task in payload.tasks if task.type != "dag_id"]
    for i in range(1, len(declared_vars)):
        lines.append(f"    {declared_vars[i - 1]} >> {declared_vars[i]}")

    os.makedirs("./airflow_dags", exist_ok=True)
    with open(dag_file_path, "w") as f:
        f.write("\n".join(lines))

    return {"message": "DAG written", "file": dag_file_name}