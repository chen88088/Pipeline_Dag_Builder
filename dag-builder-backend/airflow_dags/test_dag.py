from airflow import DAG

from airflow.operators.python import PythonOperator

from airflow.utils.dates import days_ago

from datetime import datetime



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



with DAG('test_dag', start_date=days_ago(1), schedule_interval=None) as dag:

    Generate_Execution_ID = PythonOperator(
        task_id='Generate_Execution_ID',
        python_callable=generate_execution_id,
    )