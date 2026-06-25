import os
import sys
import traceback
from pathlib import Path


def main():
    test_dir = Path('tests')
    passed = 0
    failed = 0
    sys.path.insert(0, str(Path('.').resolve()))
    for test_file in sorted(test_dir.glob('test_*.py')):
        namespace = {}
        exec(test_file.read_text(encoding='utf-8'), namespace)
        for name, obj in namespace.items():
            if name.startswith('test_') and callable(obj):
                try:
                    obj()
                    passed += 1
                    print(f'PASS {name}')
                except Exception as exc:
                    failed += 1
                    print(f'FAIL {name}: {exc}')
    print(f'Passed: {passed}, Failed: {failed}')
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
