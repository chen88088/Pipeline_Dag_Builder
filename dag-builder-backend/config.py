import os
from dotenv import load_dotenv

load_dotenv()

class Config:

    # GitLab 配置
    GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.com")
    GITLAB_ACCESS_TOKEN = os.getenv("GITLAB_ACCESS_TOKEN", "your_project_token")  # 替換為您的 Project Token
    TARGET_REPO_NAME = os.getenv("TARGET_REPO_NAME", "MLOps_Dag_Staging")  # 預設的儲存庫名稱
    DEFAULT_BRANCH = os.getenv("DEFAULT_BRANCH", "main")
    TEMPLATE_REPO_NAME = os.getenv("TEMPLATE_REPO_NAME", "MLOps_dag_template")
    TEMPLATE_FILE_PATH = os.getenv("TEMPLATE_FILE_PATH", "template.py")

    AIRFLOW_BASE_URL = os.getenv("AIRFLOW_BASE_URL", "http://10.52.52.142:30080")
    AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "admin")
    AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")