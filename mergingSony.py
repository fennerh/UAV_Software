# -*- coding: utf-8 -*-
"""
Created on Mon Nov 29 13:46:12 2021

@author: holmanf
"""
from rasterio import warp
import rasterio
import numpy as np
from osgeo import gdal
import os, shutil

##Assumes geojson has been produced with geojson tool, and plot_id provides the plot number.##

def orthoMerge(inRGB,inNIR,inDEM,inDSM,outPath):
    '''
    Merge orthomosaics into single file. LZW compression applied with 2nd predictor.

    Will perform preliminary check for sufficient disk space.

    Parameters
    ----------
    inRGB : str
        File path for RGB orthomosaic.
    inNIR : str
        File path for NIR orthomosaic.
    inDEM : str
        File path for DEM orthomosaic.
    inDSM : str
        File path for DSM orthomosaic.
    outPath : str
        File path for output file.
    '''
    print(outPath)
    disk = os.path.split(outPath)[0]
    total, used, free = shutil.disk_usage(disk)

    print("Total: %d GiB" % (total // (2**30)))
    print("Used: %d GiB" % (used // (2**30)))
    print("Free: %d GiB" % (free // (2**30)))

    if (free // (2**30)) < 20:
        print('Not enough free disk space, will need >20gb temporarily for this bad boy')
    else:
        bands = ['Blue','Green','Red','NIR']
        
        with rasterio.open(inRGB) as dest:
            with rasterio.open(inNIR) as src:
                
                profile = dest.meta.copy()
                print(profile)

                destiny = np.zeros(dest.shape,np.float32)
            
                warp.reproject(source=src.read(1),
                            destination=destiny,
                            src_transform=src.transform,
                            src_crs=src.crs,
                            dst_transform=dest.transform,
                            dst_crs=dest.crs,
                            resampling=rasterio.warp.Resampling.nearest)
        
                datas = [dest.read(3),dest.read(2),dest.read(1),destiny]

            if inDSM != '' and inDEM != '':
                with rasterio.open(inDSM) as DSM:
                    with rasterio.open(inDEM) as DEM:

                        destiny_DSM = np.zeros(dest.shape,np.float32)
                        destiny_DEM = np.zeros(dest.shape,np.float32)

                        warp.reproject(source=DSM.read(1),
                            destination=destiny_DSM,
                            src_transform=DSM.transform,
                            src_crs=DSM.crs,
                            dst_transform=dest.transform,
                            dst_crs=dest.crs,
                            resampling=rasterio.warp.Resampling.nearest)

                        warp.reproject(source=DEM.read(1),
                            destination=destiny_DEM,
                            src_transform=DEM.transform,
                            src_crs=DEM.crs,
                            dst_transform=dest.transform,
                            dst_crs=dest.crs,
                            resampling=rasterio.warp.Resampling.nearest)

                        norm_DEM = destiny_DEM - destiny_DSM
                datas.append(norm_DEM)
                bands.append('nDEM')


        with rasterio.open(outPath,'w',**profile,num_threads='all_cpus') as dst:       
            for index, value in enumerate(datas):
                print(bands[index], value.mean())
                dst.write_band(index+1,value)
                dst.set_band_description(index+1, bands[index])
        
        command_lzw_2 = "gdal_translate -of GTiff -co \"COMPRESS=LZW\" -co \"PREDICTOR=2\" -co \"TILED=YES\" -co \"BIGTIFF=YES\" " + outPathT + " " + outPath
        os.system(command_lzw_2)
        os.remove(outPathT)
        print('Done!')
    
#%% Test Cell    
if __name__ == "__main__":
    inRGB = r'E:\2017\1701_21_270717\RGB_ortho.tif'
    inNIR = r'E:\2017\1701_21_270717\NIR_ortho.tif'
    outPath = r'D:\SMs_ortho_LZW.tif'
    outPathT = r'D:\SMs_ortho_LZW_temp.tif'

    dataMerge(inRGB, inNIR, outPath)


#%% Compression Test results:
"""
           Uncompressed   Packbits Deflate pred=1 Deflate pred=2  LZW pred=1  LZW pred=2  LZW pred=3
Size                17G        10G             5G             4G          6G          4G          4G
Write time     23.87819  47.451463     196.176327     327.323451  146.912607  131.762946  144.206463
Read time     27.024627  54.662558      50.725402      44.739665   72.293431   68.033801   86.445786
"""