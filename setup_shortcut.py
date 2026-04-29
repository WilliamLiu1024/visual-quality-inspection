"""
Run once on a new machine to create a desktop shortcut for the launcher.
Usage: python setup_shortcut.py
"""
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
START_SCRIPT = PROJECT_DIR / 'start.py'


def _create_shortcut_win32com() -> Path:
    import win32com.client  # type: ignore[import]

    shell = win32com.client.Dispatch('WScript.Shell')
    desktop = Path(shell.SpecialFolders('Desktop'))
    shortcut_path = desktop / '钢材缺陷检测.lnk'

    lnk = shell.CreateShortCut(str(shortcut_path))
    lnk.TargetPath = sys.executable
    lnk.Arguments = f'"{START_SCRIPT}"'
    lnk.WorkingDirectory = str(PROJECT_DIR)
    lnk.Description = 'Steel Defect Detection'
    lnk.save()
    return shortcut_path


def _create_shortcut_ctypes() -> Path:
    """Fallback: pure ctypes, no extra packages needed."""
    import ctypes
    import ctypes.wintypes

    CLSID_ShellLink = '{00021401-0000-0000-C000-000000000046}'
    IID_IShellLink = '{000214EE-0000-0000-C000-000000000046}'
    IID_IPersistFile = '{0000010B-0000-0000-C000-000000000046}'

    CoInitialize = ctypes.windll.ole32.CoInitialize
    CoCreateInstance = ctypes.windll.ole32.CoCreateInstance
    CoUninitialize = ctypes.windll.ole32.CoUninitialize

    CoInitialize(None)

    CSIDL_DESKTOPDIRECTORY = 0x10
    buf = ctypes.create_unicode_buffer(300)
    ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_DESKTOPDIRECTORY, None, 0, buf)
    desktop = Path(buf.value)
    shortcut_path = desktop / '钢材缺陷检测.lnk'

    # Fall back to writing a plain URL shortcut if COM is tricky
    with open(shortcut_path.with_suffix('.url'), 'w', encoding='utf-8') as f:
        f.write('[InternetShortcut]\n')
        f.write(f'URL=file:///{START_SCRIPT}\n')

    CoUninitialize()
    return shortcut_path.with_suffix('.url')


def main() -> None:
    if sys.platform != 'win32':
        print('This script is Windows-only.')
        sys.exit(1)

    print('Creating desktop shortcut...')
    try:
        path = _create_shortcut_win32com()
        print(f'Shortcut created: {path}')
        print('Double-click the shortcut on the desktop to start the server.')
    except ImportError:
        print('[Info] pywin32 not installed, using fallback method...')
        path = _create_shortcut_ctypes()
        print(f'Shortcut created: {path}')
        print('Note: This is a URL shortcut — right-click it and choose "Open" to launch.')
    except Exception as exc:
        print(f'[Error] Could not create shortcut: {exc}')
        print()
        print('Manual alternative:')
        print(f'  Right-click {START_SCRIPT}')
        print('  → "Create shortcut" → move the shortcut to your desktop.')


if __name__ == '__main__':
    main()
