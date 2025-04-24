import requests
from fastapi import HTTPException
import gitlab
from dotenv import load_dotenv
load_dotenv()  # 會自動讀取 .env 檔案

from config import Config

def upload_to_gitlab(file_path: str, content: str, staging_repo_name: str = None, staging_folder: str = ""):
    """
    上傳 DAG 文件到 GitLab 指定的資料夾
    """
    upload_target_repo_name = staging_repo_name or Config.TARGET_REPO_NAME  # 默認使用目標儲存庫
    try:
        # 初始化 GitLab 連接
        gl = gitlab.Gitlab(Config.GITLAB_URL, private_token=Config.GITLAB_ACCESS_TOKEN)
        print(Config.GITLAB_URL)
        print(Config.GITLAB_ACCESS_TOKEN)
        
        # 明確驗證 token 正確性
        gl.auth()
        
        # 獲取目標專案
        project = gl.projects.get(upload_target_repo_name)

        # 如果有指定目標資料夾，將其加到 file_path 中
        if staging_folder:
            file_path = f"{staging_folder.rstrip('/')}/{file_path}"

        # 上傳文件
        project.files.create({
            'file_path': file_path,
            'branch': Config.DEFAULT_BRANCH,
            'content': content,
            'commit_message': f'Upload {file_path} to {upload_target_repo_name}'
        })
        return f"File uploaded successfully to {upload_target_repo_name}/{file_path}"
    except gitlab.exceptions.GitlabCreateError as e:
        raise Exception(f"Failed to upload file to GitLab: {e.response_code}: {e.error_message}")
    except gitlab.exceptions.GitlabAuthenticationError:
        raise Exception("Authentication failed. Check your token or permissions.")
    except gitlab.exceptions.GitlabGetError as e:
        raise Exception(f"❌ Cannot find project: {upload_target_repo_name}. Details: {e}")