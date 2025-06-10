# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('conf.yaml.example', '.'), ('src', 'src')],
    hiddenimports=['langchain_community', 'langchain_openai', 'fastapi', 'uvicorn', 'sse_starlette', 'httpx', 'readabilipy', 'python_dotenv', 'socksio', 'markdownify', 'pandas', 'numpy', 'yfinance', 'litellm', 'json_repair', 'jinja2', 'duckduckgo_search', 'inquirerpy', 'arxiv', 'mcp', 'tenacity', 'nest_asyncio'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='code_agent',
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
)
