import os
import sys
from pathlib import Path

# Disable SQLAlchemy Cython extensions to avoid Windows AppLocker DLL blocks in local dev venvs
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
