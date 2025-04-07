from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime
import os
import re

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 資料結構定義 ---
class Task(BaseModel):
    id: str
    type: str
    config: Dict[str, str]
    upstream: List[str] = []

class DAGPayload(BaseModel):
    dag_name: str
    tasks: List[Task]

# --- 輔助函式 ---
def safe_python_var(name: str) -> str:
    return re.sub(r'\W|^(?=\d)', '_', name)

# --- 函式區段（目前僅支援 generate_execution_id） ---
generate_id_func_code = """
# function to record pipeline start time as execution id
def generate_execution_id(ti):
    from datetime import datetime
    import random
    import string

    now_str = datetime.now().strftime("%Y%m%dx%H%M%S")
    rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    execution_id = f"{now_str}xx{rand_str}"
    print(f"[Generate_Execution_ID] execution_id = {execution_id}")
    ti.xcom_push(key='execution_id', value=execution_id)
""".strip()

# --- Jinja2 風格模板渲染 ---
def render_generate_id(task: Task):
    var_name = safe_python_var(task.id)
    return f"""
    {var_name} = PythonOperator(
        task_id='{task.id}',
        python_callable=generate_execution_id,
    )
    """.strip()

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
        "",
        generate_id_func_code,
        "",
        f"with DAG('{dag_name}', start_date=days_ago(1), schedule_interval=None) as dag:",
    ]

    task_blocks = []
    declared_vars = []
    for task in payload.tasks:
        if task.type == "generate_id":
            rendered = render_generate_id(task)
            task_blocks.append(rendered)
            declared_vars.append(safe_python_var(task.id))

    lines.extend([f"    {line}" if not line.startswith("    ") else line for line in task_blocks])

    # 加入依賴關係：第二個節點開始依序相接 >>
    declared_vars = [safe_python_var(task.id) for task in payload.tasks if task.type != "dag_id"]
    for i in range(1, len(declared_vars)):
        lines.append(f"    {declared_vars[i - 1]} >> {declared_vars[i]}")

    os.makedirs("./airflow_dags", exist_ok=True)
    with open(dag_file_path, "w") as f:
        f.write("\n\n".join(lines))

    return {"message": "DAG written", "file": dag_file_name}