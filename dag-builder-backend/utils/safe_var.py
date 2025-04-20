import re

def safe_python_var(name: str) -> str:
    """
    將任意字串轉成合法的 Python 變數名稱。
    - 把非法字元（非字母、數字、底線）轉成底線
    - 開頭如果是數字，加上 prefix
    """
    name = name.strip()
    name = re.sub(r'\W|^(?=\d)', '_', name)  # 非法字元轉底線，開頭是數字也加底線
    return name