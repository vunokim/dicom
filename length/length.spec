# dicom_length.spec
block_cipher = None

a = Analysis(
    ['length.py'],
    pathex=['.'],
    binaries=[],
    datas=[('D:\\github\\dicom\\length\\measure.ico', '.')],
    hiddenimports=[
        'matplotlib.backends.backend_qt5agg',
        'PyQt5.QtWidgets',
        'PyQt5.QtGui',
        'PyQt5.QtCore'
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'numba.core.datamodel.old_models',
        'numba.core.typing.old_mathdecl',
        'numba.np.old_arraymath',
        'pysqlite2',
        'MySQLdb',
        'psycopg2',
        'tbb',
        'python38.dll'
    ],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

coll = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DICOM_Length',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='D:\\github\\dicom\\length\\measure.ico'
)
