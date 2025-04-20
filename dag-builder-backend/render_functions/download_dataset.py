# render_functions/download_dataset.py
from utils.safe_var import safe_python_var

def render_download_dataset(task):
    return f"""{safe_python_var(task.id)} = PythonOperator(
    task_id=\"{task.id}\",
    python_callable=call_api_task,
    op_kwargs={{
        'info_source_task_ids': 'Create_Runtime_Env',
        'task_stage_type': 'Training',
        'route': 'Training/Download_Dataset'
    }},
    dag=dag
)"""
