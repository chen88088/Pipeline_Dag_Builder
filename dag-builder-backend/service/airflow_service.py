import time
import requests
from config import Config

def wait_for_dag_to_appear(dag_id: str, airflow_base_url: str, timeout: int = 60, interval: int = 5, auth: tuple = None) -> str:
    import time
    import requests

    print(f"⏳ 等待 Airflow 註冊 DAG：{dag_id} ...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            resp = requests.get(f"{airflow_base_url}/api/v1/dags", auth=auth)
            resp.raise_for_status()
            dag_list = resp.json().get("dags", [])

            if any(d["dag_id"] == dag_id for d in dag_list):
                print(f"✅ DAG {dag_id} 已註冊！")
                return f"{airflow_base_url}/dags/{dag_id}/grid"
        except Exception as e:
            print(f"[Airflow Check Error] {e}")

        time.sleep(interval)

    raise Exception(f"DAG {dag_id} 未在 {timeout} 秒內出現在 Airflow 中")

