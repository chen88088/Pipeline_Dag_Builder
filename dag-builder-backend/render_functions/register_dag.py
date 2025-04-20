# render_functions/register_dag.py
from utils.safe_var import safe_python_var

def render_register_dag(task):
    return f"""{safe_python_var(task.id)} = PythonOperator(
    task_id='{task.id}',
    python_callable=call_api_task,
    op_kwargs={{
        'info_source_task_ids': 'PREVIOUS_ENV_NODE',
        'task_stage_type': 'Training',
        'route': 'Training/Register_Dag'
    }},
    dag=dag
)"""