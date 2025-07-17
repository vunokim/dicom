# dicom_tag_loader.spec
# This is a PyInstaller spec file for the DICOM Viewer application.
import sys
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_submodules
 
block_cipher = None
 
datas = collect_data_files('pydicom')
datas += collect_data_files('gdcm')
datas += collect_data_files('pylibjpeg')
datas += collect_data_files('pylibjpeg-libjpeg')
datas += collect_data_files('pylibjpeg-openjpeg')
datas += collect_data_files('PyQt5')
datas += collect_data_files('numpy')
 
 
a = Analysis(
    ['dicom_tag_loader.py'],  # Input script
    pathex=[],  # Path where your script is located
    binaries=[('C:\\Python312\\Lib\\site-packages\\gdcm\\_gdcmswig.pyd', '.')],
    datas=datas,
             hiddenimports=collect_submodules('pydicom') +
                           collect_submodules('gdcm') +
                           collect_submodules('pylibjpeg') +
                           collect_submodules('numpy') +
                           collect_submodules('PyQt5'),
    hookspath=['C:\\Python312\\Lib\\site-packages'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy.f2py.tests', 'pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)
 
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
 
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    exclude_binaries=True,
    name='Dicom_Tag_Loader',  # Name of the executable
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to False if you don't want a console window
    icon=['D:\\dicom_tag_loader\\tag.ico'],
    onefile=True
)
 
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Dicom_Tag_Loader'  # Output folder name
)