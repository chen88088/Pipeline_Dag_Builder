# render_functions/create_env.py
from utils.safe_var import safe_python_var

def render_create_env(task):
    config = task.config 
    return f"""{safe_python_var(task.id)} = PythonOperator(
    task_id='{task.id}',
    python_callable=get_ml_serving_pod_info,
    op_kwargs={{
        'ml_serving_pod_image_name': '{config.get('image_name', '')}',
        'image_tag': '{config.get('image_tag', '')}',
        'export_port': {int(config.get('export_port', 8019))}
    }},
    dag=dag
)"""
