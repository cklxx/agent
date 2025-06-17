# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['langchain_community', 'langchain_openai', 'fastapi', 'uvicorn', 'litellm', 'jinja2', 'sklearn', 'sklearn.utils._cython_blas', 'sklearn.neighbors.typedefs', 'sklearn.neighbors.quad_tree', 'sklearn.tree._utils', 'sklearn.externals.six', 'sklearn.externals.joblib', 'sklearn.externals.array_api_compat', 'sklearn.externals.array_api_compat.numpy', 'sklearn.externals.array_api_compat.numpy.fft', 'numpy', 'numpy.random.common', 'numpy.random.bounded_integers', 'numpy.random.entropy', 'scipy', 'scipy.special._ufuncs_cxx', 'scipy.linalg.cython_blas', 'scipy.linalg.cython_lapack', 'scipy.integrate._odepack', 'scipy.integrate._quadpack', 'scipy.integrate._ode', 'pandas', 'pandas._libs.tslibs.timedeltas', 'pandas._libs.tslibs.np_datetime', 'pandas._libs.tslibs.nattype', 'pandas._libs.skiplist', 'charset_normalizer.md__mypyc', 'tiktoken_ext', 'tiktoken_ext.openai_public']
hiddenimports += collect_submodules('sklearn')
hiddenimports += collect_submodules('scipy')


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('conf.yaml.example', '.')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'wx'],
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
