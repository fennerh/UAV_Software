# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_data_files
sys.setrecursionlimit(5000)

block_cipher = None
import glob, os
rasterio_imports_paths = glob.glob(r'C:\\Users\\holmanf\\Anaconda3\\envs\\UavSoftware\\Lib\\site-packages\\rasterio\\*.py')
fiona_imports_paths = glob.glob(r'C:\\Users\\holmanf\\Anaconda3\\envs\\UavSoftware\\Lib\\site-packages\\fiona\\*.py')
extra_imports = ['rasterio._shim','rasterio.sample','rasterio.vrt','fiona._shim','fiona.schema','tifffile._tifffile','xlsxwriter','rasterio.control','pkg_resources.py2_warn']

for item in rasterio_imports_paths:
    current_module_filename = os.path.split(item)[-1]
    current_module_filename = 'rasterio.'+current_module_filename.replace('.py', '')
    extra_imports.append(current_module_filename)

for item in fiona_imports_paths:
    current_module_filename = os.path.split(item)[-1]
    current_module_filename = 'fiona.'+current_module_filename.replace('.py', '')
    extra_imports.append(current_module_filename)

a = Analysis(['GUI_Master.py'],
             pathex=['D:\\BitBucket\\UAV_Software\\'],
             binaries=[],
             datas=[('D:\\BitBucket\\UAV_Software\\Scripts_V2\\Requirements\\*.txt','.'),('D:\\BitBucket\\UAV_Software\\Scripts_V2\\Graphics\\*.gif','.'),('D:\\BitBucket\\UAV_Software\\Scripts_V2\\Graphics\\*.png','.'),('D:\\BitBucket\\UAV_Software\\Scripts_V2\\Requirements\\*.exe','.'),
		('D:\\BitBucket\\UAV_Software\\Scripts_V2\\Dark_images\\','Dark_images'),
		('C:\\Users\\holmanf\\Anaconda3\\envs\\UavSoftware\\Library\\share\\gdal','gdal'),('C:\\Users\\holmanf\\Anaconda3\\envs\\UavSoftware\\Library\\share\\proj','proj')],
             hiddenimports=extra_imports,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='UAV_Data_Tools',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True,
	  icon='D:\\BitBucket\\UAV_Software\\Scripts_V2\\Graphics\\ICON.ico' )