# gitshuttle.spec
# PyInstaller 스펙 파일 — 단일 실행 파일(onefile) Windows 콘솔 앱 빌드
block_cipher = None

a = Analysis(
    ['gitshuttle/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['gitshuttle', 'typer', 'click', 'rich'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='gitshuttle',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    env={'PYTHONUTF8': '1'},
)
