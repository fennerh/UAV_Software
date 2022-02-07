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

def bandCount(inFile):
    '''
    Count number of bands in given raster file

    Parameters
    ----------
    inFile : file path
        Raster file path.
    
    Return
    ---------
    a : int
        Number of bands in raster.
        
    '''
    if not inFile:
        return(0)
    else:
        with rasterio.open(inFile) as file:
            a = file.count
    return(a)

##Assumes geojson has been produced with geojson tool, and plot_id provides the plot number.##

def orthoMerge(inRGB,inNIR,inDEM,inDSM,inOther,outPath,bandNames):
    '''
    Merge multiple raster datasets together into single multi-band file for improved storage and analysis.

    LZW (predictor = 2) compression applied to final output.

    Parameters
    ----------
    inRGB : File
        File path to RGB raster dataset
    inNIR : File
        File path to NIR raster dataset
    inDEM : File
        File path to Digital Elevation Model raster dataset
    inDSM : File
        File path to Digital Surface Model raster dataset
    inOther : dict
        Dictionary containing file path to additional raster dataset, and str of file name.
    outPath : file Path
        Output file path.
    bandNames : list
        List of all bandnames from all input datasets.
    '''

    disk = os.path.split(outPath)[0]
    total, used, free = shutil.disk_usage(disk)

    print("Total: %d GiB" % (total // (2**30)))
    print("Used: %d GiB" % (used // (2**30)))
    print("Free: %d GiB" % (free // (2**30)))

    outPathT = os.path.splitext(outPath)[0]+'_temp.tif'

    if (free // (2**30)) < 20:
        print('Not enough free disk space, will need >20gb temporarily for this bad boy')
        return
    else:
        bands = [a for a in bandNames.split(', ')]
        print(bands)

    bandCnt = bandCount(inRGB)
    if bandCount(inNIR) == 2:
         bandCnt += (bandCount(inNIR))
    else: bandCnt += (bandCount(inNIR)) + 1
    bandCnt += bandCount(inDSM)
    bandCnt += bandCount(inOther[1])
    print(bandCnt)
       
    with rasterio.open(inRGB) as dest:
        profile = dest.meta.copy()
        profile.update(count=bandCnt)
        with rasterio.open(outPathT,'w',**profile,num_threads='all_cpus') as dst:
            count=0
            for i in range(0,dest.count):  
                print(bands[i])
                dst.write_band(i+1,dest.read(i+1))
                dst.set_band_description(i+1, bands[i])   
                count+=1
            
            if inNIR != '':
                print('NIR')
                with rasterio.open(inNIR) as src:
                    
                    destiny = np.zeros(dest.shape,np.float32)
                
                    warp.reproject(source=src.read(1),
                                destination=destiny,
                                src_transform=src.transform,
                                src_crs=src.crs,
                                dst_transform=dest.transform,
                                dst_crs=dest.crs,
                                resampling=rasterio.warp.Resampling.nearest)
                count+=1
                dst.write_band(count,destiny)
                dst.set_band_description(count, 'NIR')
                
                if any(['RED' == s.upper() for i,s in enumerate(bands)]):
                    index = [i for i, s in enumerate(bands) if 'RED' in s.upper()]
                    print('NDVI')
                    ndvi = (destiny - dest.read(index[0]+1))/(destiny + dest.read(index[0]+1))
                    dst.write_band(count+1,ndvi)
                    dst.set_band_description(count+1, 'NDVI')
            destiny = None
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
                count+=1
                dst.write_band(count+1,norm_DEM)
                dst.set_band_description(count+1, 'NIR')
            destiny_DSM = None
            destiny_DEM = None

            if inDSM != '' and inDEM == '':
                with rasterio.open(inDSM) as DSM:
                    destiny_DSM = np.zeros(dest.shape,np.float32)
                    warp.reproject(source=DSM.read(1),
                            destination=destiny_DSM,
                            src_transform=DSM.transform,
                            src_crs=DSM.crs,
                            dst_transform=dest.transform,
                            dst_crs=dest.crs,
                            resampling=rasterio.warp.Resampling.nearest)
                count+=1
                dst.write_band(count+1,destiny_DSM)
                dst.set_band_description(count+1, 'DSM')
            destiny_DSM=None

            if inOther[1] != '':
                print(inOther)
                with rasterio.open(inOther[1]) as other:
                    destiny_other = np.zeros(dest.shape,np.float32)

                    warp.reproject(source=other.read(1),
                            destination=destiny_other,
                            src_transform=other.transform,
                            src_crs=other.crs,
                            dst_transform=dest.transform,
                            dst_crs=dest.crs,
                            resampling=rasterio.warp.Resampling.nearest)
                count+=1
                dst.write_band(count+1,destiny_other)
                dst.set_band_description(count+1,inOther[0])
            destiny_other=None
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

    orthoMerge(inRGB, inNIR, outPath)

#%% Compression Test results:
"""
           Uncompressed   Packbits Deflate pred=1 Deflate pred=2  LZW pred=1  LZW pred=2  LZW pred=3
Size                17G        10G             5G             4G          6G          4G          4G
Write time     23.87819  47.451463     196.176327     327.323451  146.912607  131.762946  144.206463
Read time     27.024627  54.662558      50.725402      44.739665   72.293431   68.033801   86.445786
"""