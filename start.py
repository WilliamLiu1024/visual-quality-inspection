"""
Steel Defect Detection - Launcher
Double-click this file to start (requires Python 3 installed and .py associated with Python).
Or run: python start.py
"""
import os
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
VENV_DIR = PROJECT_DIR / '.venv'
VENV_PYTHON = VENV_DIR / 'Scripts' / 'python.exe'
REQUIREMENTS = PROJECT_DIR / 'backend' / 'requirements.txt'
HOST = '127.0.0.1'
PORT = 8000

_child: subprocess.Popen | None = None


def _kill_child() -> None:
    global _child
    if _child and _child.poll() is None:
        # 用 taskkill /T 递归杀掉整个进程树（含孙进程）
        subprocess.call(
            ['taskkill', '/F', '/T', '/PID', str(_child.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            _child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            _child.kill()
    _child = None


def _sigint_handler(sig, frame) -> None:
    print('\n[Stop] 正在停止服务...')
    _kill_child()
    sys.exit(0)


def _in_venv() -> bool:
    return sys.prefix != sys.base_prefix


def _find_system_python() -> str:
    for candidate in ('python', 'python3'):
        try:
            result = subprocess.run(
                [candidate, '--version'],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and 'Python 3' in result.stdout + result.stderr:
                return candidate
        except FileNotFoundError:
            continue
    raise RuntimeError('Python 3 not found. Please install Python 3 and add it to PATH.')


def _ensure_venv() -> None:
    if not VENV_PYTHON.exists():
        print('[Setup] Creating virtual environment...')
        python = _find_system_python()
        subprocess.run([python, '-m', 'venv', str(VENV_DIR)], check=True)
        print('[Setup] Virtual environment created.')


def _ensure_deps() -> None:
    result = subprocess.run(
        [str(VENV_PYTHON), '-c', 'import uvicorn'],
        capture_output=True,
    )
    if result.returncode != 0:
        print('[Setup] Installing dependencies (needs network)...')
        subprocess.run(
            [str(VENV_PYTHON), '-m', 'pip', 'install', '-r', str(REQUIREMENTS)],
            check=True,
        )
        print('[Setup] Dependencies installed.')


def _open_browser() -> None:
    def _delayed():
        time.sleep(5)
        webbrowser.open(f'http://{HOST}:{PORT}/')
    threading.Thread(target=_delayed, daemon=True).start()


def main() -> None:
    global _child
    os.chdir(PROJECT_DIR)

    # 注册 Ctrl+C 信号处理，确保子进程被强制终止
    signal.signal(signal.SIGINT, _sigint_handler)
    signal.signal(signal.SIGTERM, _sigint_handler)

    if not _in_venv():
        _ensure_venv()
        _ensure_deps()
        print('[Start] Relaunching inside virtual environment...')
        _child = subprocess.Popen([str(VENV_PYTHON), str(__file__)] + sys.argv[1:])
        try:
            _child.wait()
        except KeyboardInterrupt:
            _kill_child()
        sys.exit(0)

    os.environ['DETECTOR_NAME'] = 'yolo26'
    _open_browser()
    print(f'[Start] 服务运行在 http://{HOST}:{PORT}/ — 按 Ctrl+C 停止')

    import uvicorn
    uvicorn.run(
        'backend.app.main:app',
        host='0.0.0.0',
        port=PORT,
        log_level='info',
        timeout_graceful_shutdown=2,  # 最多等 2 秒，超时强制退出
    )


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print(f'\n[Error] {exc}')
        input('Press Enter to exit...')
        sys.exit(1)
