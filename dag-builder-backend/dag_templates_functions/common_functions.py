generate_execution_id_code = """
def generate_execution_id(ti):
    from datetime import datetime
    import random
    import string
    now_str = datetime.now().strftime("%Y%m%dx%H%M%S")
    rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    execution_id = f"{now_str}xx{rand_str}"
    print(f"[Generate_Execution_ID] execution_id = {execution_id}")
    ti.xcom_push(key='execution_id', value=execution_id)
"""

get_ml_serving_pod_info_code = """
def get_ml_serving_pod_info(ti, ml_serving_pod_image_name, image_tag, export_port):
    from airflow.hooks.http_hook import HttpHook
    dag_id = ti.dag_id
    execution_id = ti.xcom_pull(key='execution_id', task_ids='Generate_Execution_ID')
    http_hook = HttpHook(http_conn_id='controller_connection', method='POST')
    endpoint = f'/create_pod'
    body = {
        "image_name": ml_serving_pod_image_name,
        "image_tag": image_tag,
        "export_port": export_port
    }
    response = http_hook.run(endpoint, json=body)
    result = response.json()
    ti.xcom_push(key='assigned_service_instance', value=result.get('pod_name'))
    ti.xcom_push(key='assigned_ip', value=result.get('pod_service'))
    ti.xcom_push(key='assigned_port', value=export_port)
"""

call_api_task_code = """
def call_api_task(ti, info_source_task_ids, task_stage_type, route):
    import requests
    from confluent_kafka import Producer
    import json
    assigned_ip = ti.xcom_pull(key='assigned_ip', task_ids=info_source_task_ids)
    assigned_port = ti.xcom_pull(key='assigned_port', task_ids=info_source_task_ids)
    execution_id = ti.xcom_pull(key='execution_id', task_ids='Generate_Execution_ID')
    dag_id = ti.dag_id
    url = f"http://{assigned_ip}:{assigned_port}/{route}"
    body = {
        "DAG_ID": dag_id,
        "EXECUTION_ID": execution_id,
        "TASK_STAGE_TYPE": task_stage_type
    }
    response = requests.post(url, json=body)
    result = response.json()
    producer = Producer({'bootstrap.servers': 'kafka-headless.kafka.svc.cluster.local:9092'})
    producer.produce('test-log', value=json.dumps({
        "DAG_ID": dag_id,
        "EXECUTION_ID": execution_id,
        "TASK_ID": route,
        "TASK_API_RESPOND": result,
    }))
    producer.flush()
"""
