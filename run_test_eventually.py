import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))
from tests.test_week1 import test_eventually

if __name__ == '__main__':
    try:
        test_eventually()
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise
