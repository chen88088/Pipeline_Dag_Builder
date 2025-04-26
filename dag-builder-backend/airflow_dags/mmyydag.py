from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime
import requests
import json
import random
import string
from airflow.hooks.http_hook import HttpHook
from confluent_kafka import Producer

def send_message_to_kafka(message, kafka_conf, topic):
    producer = Producer(kafka_conf)
    producer.produce(topic, value=json.dumps(message))
    producer.flush()

def get_ml_serving_pod_info(ti, image_name, image_tag, export_port):
    http_hook = HttpHook(http_conn_id='controller_connection', method='POST')
    body = {"image_name": image_name, "image_tag": image_tag, "export_port": export_port} 
    response = http_hook.run('/create_pod', json=body)
    result = response.json()
    ti.xcom_push(key='assigned_service_instance', value=result['pod_name'])
    ti.xcom_push(key='assigned_ip', value=result['pod_service'])
    ti.xcom_push(key='assigned_port', value=export_port)

def delete_ml_serving_pod(ti, info_source_task_ids):
    pod_name = ti.xcom_pull(key='assigned_service_instance', task_ids=info_source_task_ids)
    http_hook = HttpHook(http_conn_id='controller_connection', method='DELETE')
    http_hook.run(f'/delete_pod/{pod_name}')

class ApiCaller:
    def __init__(self, ti, info_source_task_ids, route, body, kafka_conf, kafka_topic):
        self.ti = ti
        self.route = route
        self.body = body
        self.kafka_conf = kafka_conf
        self.kafka_topic = kafka_topic
        self.ip = ti.xcom_pull(key='assigned_ip', task_ids=info_source_task_ids)
        self.port = ti.xcom_pull(key='assigned_port', task_ids=info_source_task_ids)

    def call_api(self):
        url = f"http://{self.ip}:{self.port}/{self.route}"
        resp = requests.post(url, json=self.body)
        result = resp.json()
        send_message_to_kafka({"TASK_ID": self.route, "TASK_API_RESPOND": result}, self.kafka_conf, self.kafka_topic)

def call_api_task(ti, info_source_task_ids, route, body, kafka_conf, kafka_topic):
    dag_run = ti.get_dagrun()
    reserved_run_id = dag_run.conf.get('reserved_run_id') if dag_run else None
    if reserved_run_id:
        body = dict(body)  # 複製一份，避免汙染到原本的 body_config
        body['reserved_run_id'] = reserved_run_id
    ApiCaller(ti, info_source_task_ids, route, body, kafka_conf, kafka_topic).call_api()

body_config = {   'CODE_REPO_URL': {   'Training': 'https://github.com/chen88088/Prediction-of-Car-Insurance-Claim.git'},
    'DAG_ID': 'mmyydag',
    'DATASET_DVCFILE_REPO': 'https://github.com/chen88088/car-insurance-dataset.git',
    'DATASET_NAME': 'car-insurance',
    'DATASET_VERSION': 'v1',
    'DEPLOYER_EMAIL': 'peng@example.com',
    'DEPLOYER_NAME': 'Peng Sheng',
    'EXECUTION_ID': '20250426x081222xxp7kqxm',
    'EXECUTION_SCRIPTS': {'Training': ['lightgbmoptimization.py']},
    'IMAGE_NAME': {'Training': 'moa_ncu/car-insurance-lightgbm-training'},
    'MODEL_NAME': '',
    'MODEL_VERSION': '',
    'PIPELINE_CONFIG': {   'params': {   'learning_rate': 0.01,
                                         'max_depth': 6,
                                         'n_estimators': 200,
                                         'num_leaves': 50}},
    'TASK_STAGE_TYPE': 'Training',
    'UPLOAD_MLFLOW_SCRIPT': {'Training': 'lightgbmoptimization_result_to_mlflow.py'}}
kafka_conf = {"bootstrap.servers": "kafka-0.kafka-headless.kafka.svc.cluster.local:9092,kafka-1.kafka-headless.kafka.svc.cluster.local:9092,kafka-2.kafka-headless.kafka.svc.cluster.local:9092"}
kafka_topic = 'test-log'

with DAG('mmyydag', start_date=days_ago(1), schedule_interval=None) as dag:
    node_1_create_env = PythonOperator(task_id='node_1_create_env', python_callable=get_ml_serving_pod_info, op_kwargs={'image_name': 'moa_ncu/general-model-training-server', 'image_tag': 'latest', 'export_port': 8019})
    node_2_register_dag = PythonOperator(
                task_id='node_2_register_dag',
                python_callable=call_api_task,
                op_kwargs={
                    'info_source_task_ids': 'node_1_create_env',
                    'route': 'Training/Register_Dag',
                    'body': body_config,
                    'kafka_conf': kafka_conf,
                    'kafka_topic': kafka_topic
                }
            )
    node_3_download_dataset = PythonOperator(
                task_id='node_3_download_dataset',
                python_callable=call_api_task,
                op_kwargs={
                    'info_source_task_ids': 'node_1_create_env',
                    'route': 'Training/Download_Dataset',
                    'body': body_config,
                    'kafka_conf': kafka_conf,
                    'kafka_topic': kafka_topic
                }
            )
    node_4_download_code = PythonOperator(
                task_id='node_4_download_code',
                python_callable=call_api_task,
                op_kwargs={
                    'info_source_task_ids': 'node_1_create_env',
                    'route': 'Training/Download_CodeRepo',
                    'body': body_config,
                    'kafka_conf': kafka_conf,
                    'kafka_topic': kafka_topic
                }
            )
    node_5_add_config = PythonOperator(
                task_id='node_5_add_config',
                python_callable=call_api_task,
                op_kwargs={
                    'info_source_task_ids': 'node_1_create_env',
                    'route': 'Training/Add_Config',
                    'body': body_config,
                    'kafka_conf': kafka_conf,
                    'kafka_topic': kafka_topic
                }
            )
    node_6_run_script = PythonOperator(
                task_id='node_6_run_script',
                python_callable=call_api_task,
                op_kwargs={
                    'info_source_task_ids': 'node_1_create_env',
                    'route': 'Training/Execute_TrainingScripts',
                    'body': body_config,
                    'kafka_conf': kafka_conf,
                    'kafka_topic': kafka_topic
                }
            )
    node_7_upload_mlflow = PythonOperator(
                task_id='node_7_upload_mlflow',
                python_callable=call_api_task,
                op_kwargs={
                    'info_source_task_ids': 'node_1_create_env',
                    'route': 'Training/Upload_ExperimentResult',
                    'body': body_config,
                    'kafka_conf': kafka_conf,
                    'kafka_topic': kafka_topic
                }
            )
    node_8_upload_log = PythonOperator(
                task_id='node_8_upload_log',
                python_callable=call_api_task,
                op_kwargs={
                    'info_source_task_ids': 'node_1_create_env',
                    'route': 'Training/Upload_Log',
                    'body': body_config,
                    'kafka_conf': kafka_conf,
                    'kafka_topic': kafka_topic
                }
            )
    node_9_release_env = PythonOperator(task_id='node_9_release_env', python_callable=delete_ml_serving_pod, op_kwargs={'info_source_task_ids': 'node_1_create_env'})
    node_1_create_env >> node_2_register_dag
    node_2_register_dag >> node_3_download_dataset
    node_3_download_dataset >> node_4_download_code
    node_4_download_code >> node_5_add_config
    node_5_add_config >> node_6_run_script
    node_6_run_script >> node_7_upload_mlflow
    node_7_upload_mlflow >> node_8_upload_log
    node_8_upload_log >> node_9_release_env