from utils.safe_var import safe_python_var

def render_generate_id(task):
    return f"""{safe_python_var(task.id)} = PythonOperator(
    task_id="{task.id}",
    python_callable=generate_execution_id,
    dag=dag
)"""
