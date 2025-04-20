from .generate_id import render_generate_id
from .create_env import render_create_env
from .register_dag import render_register_dag
from .download_dataset import render_download_dataset
# ... 其他的

TASK_RENDERERS = {
    "generate_id": render_generate_id,
    "create_env": render_create_env,
    "register_dag": render_register_dag,
    "download_dataset": render_download_dataset,
    # ...對應前端元件的 type
}
