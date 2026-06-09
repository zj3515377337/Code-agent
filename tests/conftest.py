"""共享测试夹具。"""
import sys
from pathlib import Path

# 确保 src 在导入路径中
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
