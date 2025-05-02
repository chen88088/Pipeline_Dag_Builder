# === dag_api_service.py ===
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any
import os
import json
from utils.safe_var import safe_python_var
from fastapi.middleware.cors import CORSMiddleware
import pprint
from datetime import datetime
import random
import string
from fastapi import HTTPException
from service.gitlab_service import upload_to_gitlab
from service.airflow_service import wait_for_dag_to_appear
from config import Config
import requests
from urllib.parse import quote
import mlflow


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Kafka config ---
KAFKA_CONF = {
    'bootstrap.servers': 'kafka-0.kafka-headless.kafka.svc.cluster.local:9092,'
                         'kafka-1.kafka-headless.kafka.svc.cluster.local:9092,'
                         'kafka-2.kafka-headless.kafka.svc.cluster.local:9092'
}
KAFKA_TOPIC = 'test-log'

# --- General Training Server config ---
GENERAL_TRAINING_SERVER_IMAGE_NAME = 'moa_ncu/general-model-training-server'
GENERAL_TRAINING_SERVER_IMAGE_TAG = 'latest'
GENERAL_TRAINING_SERVER_IMAGE_PORT =  '8019'

# --- Schema 定義 ---
class Task(BaseModel):
    id: str
    type: str
    config: Dict[str, Any]
    upstream: List[str]

class DAGPayload(BaseModel):
    dag_name: str
    tasks: List[Task]

def extract_global_body_from_tasks(payload: DAGPayload) -> tuple:
    merged_config = {}
    for task in payload.tasks:
        merged_config.update(task.config)

    now_str = datetime.now().strftime("%Y%m%dx%H%M%S")
    rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    execution_id = f"{now_str}xx{rand_str}"

    def parse_value(v):
        try:
            return int(v)
        except ValueError:
            try:
                return float(v)
            except ValueError:
                return v

    return execution_id, {
        "DAG_ID": payload.dag_name,
        "EXECUTION_ID": execution_id,
        "TASK_STAGE_TYPE": "Training",
        "DATASET_NAME": merged_config.get("dataset_name"),
        "DATASET_VERSION": merged_config.get("dataset_version"),
        "DATASET_DVCFILE_REPO": merged_config.get("dvc_repo"),
        "CODE_REPO_URL": {"Training": merged_config.get("code_repo_url")},
        "IMAGE_NAME": {"Training": merged_config.get("image_name")},
        "EXECUTION_SCRIPTS": {"Training": merged_config.get("script_list")},
        "UPLOAD_MLFLOW_SCRIPT": {"Training": merged_config.get("script_name")},
        "MODEL_NAME": "",
        "MODEL_VERSION": "",
        "DEPLOYER_NAME": "Peng Sheng",
        "DEPLOYER_EMAIL": "peng@example.com",
        "PIPELINE_CONFIG": {
            "params": {
                param["key"]: parse_value(param["value"])
                for task in payload.tasks
                for param in task.config.get("config_params", [])
            }
        }
    }

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
        "import requests",
        "import json",
        "import random",
        "import string",
        "from airflow.hooks.http_hook import HttpHook",
        "from confluent_kafka import Producer",
        "",
        "def send_message_to_kafka(message, kafka_conf, topic):",
        "    producer = Producer(kafka_conf)",
        "    producer.produce(topic, value=json.dumps(message))",
        "    producer.flush()",
        "",
        "def get_ml_serving_pod_info(ti, image_name, image_tag, export_port):",
        "    http_hook = HttpHook(http_conn_id='controller_connection', method='POST')",
        "    body = {\"image_name\": image_name, \"image_tag\": image_tag, \"export_port\": export_port} ",
        "    response = http_hook.run('/create_pod', json=body)",
        "    result = response.json()",
        "    ti.xcom_push(key='assigned_service_instance', value=result['pod_name'])",
        "    ti.xcom_push(key='assigned_ip', value=result['pod_service'])",
        "    ti.xcom_push(key='assigned_port', value=export_port)",
        "",
        "def delete_ml_serving_pod(ti, info_source_task_ids):",
        "    pod_name = ti.xcom_pull(key='assigned_service_instance', task_ids=info_source_task_ids)",
        "    http_hook = HttpHook(http_conn_id='controller_connection', method='DELETE')",
        "    http_hook.run(f'/delete_pod/{pod_name}')",
        "",
        "class ApiCaller:",
        "    def __init__(self, ti, info_source_task_ids, route, body, kafka_conf, kafka_topic):",
        "        self.ti = ti",
        "        self.route = route",
        "        self.body = body",
        "        self.kafka_conf = kafka_conf",
        "        self.kafka_topic = kafka_topic",
        "        self.ip = ti.xcom_pull(key='assigned_ip', task_ids=info_source_task_ids)",
        "        self.port = ti.xcom_pull(key='assigned_port', task_ids=info_source_task_ids)",
        "",
        "    def call_api(self):",
        "        url = f\"http://{self.ip}:{self.port}/{self.route}\"",
        "        resp = requests.post(url, json=self.body)",
        "        result = resp.json()",
        "        send_message_to_kafka({\"TASK_ID\": self.route, \"TASK_API_RESPOND\": result}, self.kafka_conf, self.kafka_topic)",
        "",
        "def call_api_task(ti, info_source_task_ids, route, body, kafka_conf, kafka_topic):",
        "    dag_run = ti.get_dagrun()",
        "    reserved_exp_run_id = dag_run.conf.get('reserved_exp_run_id') if dag_run else None",
        "    if reserved_exp_run_id:",
        "        body = dict(body)  # 複製一份，避免汙染到原本的 body_config",
        "        body['reserved_exp_run_id'] = reserved_exp_run_id",
        "    ApiCaller(ti, info_source_task_ids, route, body, kafka_conf, kafka_topic).call_api()",
        ""
    ]

    execution_id, global_body = extract_global_body_from_tasks(payload)
    body_str = pprint.pformat(global_body, indent=4, width=100)
    lines.append("body_config = " + body_str)
    lines.append(f"kafka_conf = {json.dumps(KAFKA_CONF)}")
    lines.append(f"kafka_topic = '{KAFKA_TOPIC}'")
    lines.append("")
    lines.append(f"with DAG('{dag_name}', start_date=days_ago(1), schedule_interval=None) as dag:")

    task_blocks = []
    declared_vars = []

    route_map = {
        "register_dag": "Training/Register_Dag",
        "download_dataset": "Training/Download_Dataset",
        "download_code": "Training/Download_CodeRepo",
        "add_config": "Training/Add_Config",
        "run_script": "Training/Execute_TrainingScripts",
        "upload_mlflow": "Training/Upload_ExperimentResult",
        "upload_log": "Training/Upload_Log"
    }

    create_env_varname = None

    for i, task in enumerate(payload.tasks):
        task_type_suffix = task.type.lower()
        varname = f"node_{i+1}_{task_type_suffix}"
        if task.type == "create_env":
            create_env_varname = varname
            rendered = f"{varname} = PythonOperator(task_id='{varname}', python_callable=get_ml_serving_pod_info, op_kwargs={{'image_name': '{GENERAL_TRAINING_SERVER_IMAGE_NAME}', 'image_tag': '{GENERAL_TRAINING_SERVER_IMAGE_TAG}', 'export_port': {int(GENERAL_TRAINING_SERVER_IMAGE_PORT)}}})"
        elif task.type == "release_env":
            rendered = f"{varname} = PythonOperator(task_id='{varname}', python_callable=delete_ml_serving_pod, op_kwargs={{'info_source_task_ids': '{create_env_varname}'}})"
        elif task.type in route_map:
            route = route_map[task.type]
            rendered = f"""{varname} = PythonOperator(
                task_id='{varname}',
                python_callable=call_api_task,
                op_kwargs={{
                    'info_source_task_ids': '{create_env_varname}',
                    'route': '{route}',
                    'body': body_config,
                    'kafka_conf': kafka_conf,
                    'kafka_topic': kafka_topic
                }}
            )"""
        else:
            continue

        task_blocks.append(f"    {rendered}")
        declared_vars.append(varname)

    lines.extend(task_blocks)

    for task in payload.tasks:
        this_var = f"node_{payload.tasks.index(task)+1}_{task.type.lower()}"
        for up in task.upstream:
            upstream_matches = [t for t in payload.tasks if t.id == up]
            if not upstream_matches:
                print(f"[Warning] Skipping undefined upstream task_id: {up}")
                continue
            upstream_task = upstream_matches[0]
            up_var = f"node_{payload.tasks.index(upstream_task)+1}_{upstream_task.type.lower()}"
            lines.append(f"    {up_var} >> {this_var}")

    os.makedirs("./airflow_dags", exist_ok=True)
    with open(dag_file_path, "w") as f:
        f.write("\n".join(lines))

    # === 讀取 DAG 內容並上傳到 GitLab ===
    try:
        with open(dag_file_path, "r") as f:
            dag_content = f.read()

        upload_result = upload_to_gitlab(
            file_path=dag_file_name,
            content=dag_content,
            staging_folder="dags"  # 例如存到 GitLab 的 dags 資料夾
        )

        # 等待 DAG 出現在 Airflow 中（輪詢）
        airflow_base_url = Config.AIRFLOW_BASE_URL  # 根據你實際情況修改
        dag_url = wait_for_dag_to_appear(
            dag_id=dag_name, 
            airflow_base_url=airflow_base_url,
            timeout=300,
            auth=(Config.AIRFLOW_USERNAME, Config.AIRFLOW_PASSWORD)
        )

        print(f"airflow_url: {dag_url}")

        return {
            "message": "DAG uploaded and registered in Airflow",
            "dag_id": dag_name,
            "execution_id": execution_id,
            "airflow_url": dag_url,
            "body_config": global_body
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class TriggerRequest(BaseModel):
    dag_id: str
    conf: dict = {}  # Optional, 可空白

@app.post("/trigger-dag")
def trigger_dag_run(request: TriggerRequest):
    
    auth = (Config.AIRFLOW_USERNAME, Config.AIRFLOW_PASSWORD)
    base = Config.AIRFLOW_BASE_URL

    # ✅ Step 1: 預約一個空的 run_id
    try:
        experiment_name = request.conf.get("experiment_name")
        experiment_run_name = request.conf.get("experiment_run_name")
        body_config = request.conf.get("body_config")

        if not experiment_name or not experiment_run_name:
            raise HTTPException(status_code=400, detail="experiment_name and experiment_run_name are required in conf")
        
        if not body_config:
            raise HTTPException(status_code=400, detail="body_config is required in conf")
        
        mlflow.set_tracking_uri("http://10.52.52.142:5000")

        mlflow.set_experiment(experiment_name)
        run = mlflow.start_run(run_name=experiment_run_name)
        mlflow_exp_run_id = run.info.run_id

        # ✅ 這裡直接設定 tags：把整個 request.conf 壓成 tags
        tags_to_set = {f"{k}": str(v) for k, v in request.conf.items()}
        mlflow.set_tags(tags_to_set)

        mlflow.log_param("reserved", "true")


        mlflow.end_run()  # 先關掉，之後 server 會用 run_id來繼續

        # 把預約好的 run_id 放進 conf
        request.conf["reserved_exp_run_id"] = mlflow_exp_run_id

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reserve MLflow run: {e}")

    # ✅ Step 2: Unpause the DAG
    try:
        unpause_url = f"{base}/api/v1/dags/{request.dag_id}"
        unpause_payload = { "is_paused": False }
        unpause_resp = requests.patch(unpause_url, json=unpause_payload, auth=auth)
        unpause_resp.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unpause DAG: {e}")
    
    

    # ✅ Step 3: Trigger the DAG
    try:
        trigger_url = f"{Config.AIRFLOW_BASE_URL}/api/v1/dags/{request.dag_id}/dagRuns"
        payload = {
            "conf": request.conf
        }
        
        resp = requests.post(trigger_url, json=payload, auth=auth)
        resp.raise_for_status()
        return {
            "message": f"DAG {request.dag_id} triggered successfully.",
            "dag_run_id": resp.json().get("dag_run_id", "unknown"),
            "reserved_exp_run_id": mlflow_exp_run_id,
            "trigger_time": resp.json().get("execution_date", "unknown")
        }
    except requests.HTTPError as e:
        raise HTTPException(status_code=resp.status_code, detail=f"Failed to trigger DAG: {resp.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    
def get_experiment_id_by_name(experiment_name: str) -> str:
    mlflow_server = "http://10.52.52.142:5000"
    url = f"{mlflow_server}/api/2.0/mlflow/experiments/get-by-name?experiment_name={experiment_name}"
    resp = requests.get(url)
    if resp.status_code != 200:
        raise Exception(f"❌ 查詢 experiment_id 失敗: {resp.text}")
    data = resp.json()
    return data["experiment"]["experiment_id"]

@app.get("/dag-status")
def check_dag_status(dag_id: str, execution_id: str, dag_run_id: str, reserved_exp_run_id:str):
    auth = (Config.AIRFLOW_USERNAME, Config.AIRFLOW_PASSWORD)
    base = Config.AIRFLOW_BASE_URL

    # 必須 encode run_id !!!
    encoded_run_id = quote(dag_run_id, safe="")  # safe="" 表示全編碼

    url = f"{base}/api/v1/dags/{dag_id}/dagRuns/{encoded_run_id}"

    print(f"打 API URL：{url}")

    resp = requests.get(url, auth=auth)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    state = resp.json().get("state")

    if state == "success":
        
        experiment_name = dag_id  # 你可以用 dag_id或body_config帶的
        experiment_id = get_experiment_id_by_name(experiment_name)
        execution_id = execution_id
        dag_id = dag_id

        pipeline_unique_id =f'{dag_id}_{execution_id}' 

        mlflow_url = f"http://10.52.52.142:5000/#/experiments/{experiment_id}/runs/{reserved_exp_run_id}"
        minio_url = f"http://10.52.52.138:30000/browser/testdvcfilemanagementfordag/{pipeline_unique_id}/"
        kibana_url = f"http://10.52.52.142:30601/app/discover#/?q=execution_id:{execution_id}"
        
        return {
            "state": "success",
            "mlflow_url": mlflow_url,
            "kibana_url": kibana_url,
            "minio_url": minio_url
        }
    else:
        return {"state": state}