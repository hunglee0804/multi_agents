import sys
import os

# Setup đường dẫn y hệt như test.py
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from multi_agents.config.config import *
from multi_agents.config.variable import PARENT_DB, CHILD_DB
from multi_agents.tools.react_tool import load_vector_store

def check_database():
    print("\n" + "="*40)
    print("KIỂM TRA CHROMA DATABASE")
    print("="*40)

    # Xử lý đường dẫn tương đối (từ ./database/... thành đường dẫn tuyệt đối)
    parent_path = os.path.join(project_root, PARENT_DB.replace("./", ""))
    child_path = os.path.join(project_root, CHILD_DB.replace("./", ""))

    # Kiểm tra Parent DB
    print(f"\n1. Đang kiểm tra Parent DB tại:\n   {parent_path}")
    try:
        parent_store = load_vector_store(parent_path)
        parent_data = parent_store.get()
        count = len(parent_data['ids'])
        print(f"   -> Kết quả: Có {count} tài liệu.")
    except Exception as e:
        print(f"   -> Lỗi: Không thể đọc DB. Chi tiết: {e}")

    # Kiểm tra Child DB
    print(f"\n2. Đang kiểm tra Child DB tại:\n   {child_path}")
    try:
        child_store = load_vector_store(child_path)
        child_data = child_store.get()
        count = len(child_data['ids'])
        print(f"   -> Kết quả: Có {count} tài liệu.")
    except Exception as e:
        print(f"   -> Lỗi: Không thể đọc DB. Chi tiết: {e}")
        
    print("\n" + "="*40)

if __name__ == "__main__":
    check_database()