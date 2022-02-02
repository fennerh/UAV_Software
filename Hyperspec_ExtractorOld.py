# -*- coding: utf-8 -*-
"""
Created on Mon Oct 25 14:35:17 2021

@author: holmanf
"""
import rasterio
from rasterio.features import rasterize
from rasterio.windows import from_bounds
import pandas as pd
import numpy as np
from shapely.geometry import shape
from shapely.geometry.multipolygon import MultiPolygon
import geopandas
import os, re

def overlaps_flightline(flightline, shapefiles):
    '''
    Select only shapefile which overlap flightline.

    Parameters
    ----------
    flightline : rasterio Dataset
        Any geospatial raster dataset, which overlapping shapefiles will be tested.
    shapefiles : GeoJSON
        GeoJSON file of AOI polygons, CRS:4326.

    Returns
    -------
    a : geopandas DataFrame
        Dataframe of polygons that overlap flightline.

    '''
    
    def intersect_area(lilBox, bigBox):
        
        area_covered = (lilBox.intersection(bigBox).area/lilBox.area)*100
        return round(area_covered)

    with rasterio.open(flightline) as img_rstr:
        bnd_rstr = img_rstr.read(int(img_rstr.count/2))
        rstr_crs = img_rstr.crs
        
    bnd_rstr[bnd_rstr>0]=1
    shapes = list(rasterio.features.shapes(bnd_rstr, transform=img_rstr.transform))    
          
    polygons = [shape(geom) for geom, value in shapes if value == 1]
    multipolygon = MultiPolygon(polygons)
    
    pandaPlots = geopandas.read_file(shapefiles)
    pandaPlots.to_crs(rstr_crs, inplace=True)
 
    plot, area = [],[]
    for a in pandaPlots.plot_id:
        if intersect_area(pandaPlots[pandaPlots['plot_id']==a].geometry.iloc[0],multipolygon) >= 70:
            plot.append(a)
            area.append(intersect_area(pandaPlots[pandaPlots['plot_id']==a].geometry.iloc[0],multipolygon))
        
    if len(plot) == 0:
        raise ValueError('No polygons overlap Raster layer, double check input data')
    
    df = pandaPlots[pandaPlots['plot_id'].isin(plot)].copy()
    df.loc[:,'Area'] = area

    return df

def extract_hyperspec(datafile, shapefiles,samples):
    '''
    1) Isolate polygons which cover the same area as datafile.
    
    2)Sample means of individual datafile layers/bands from each overlapping polygon.
    
    Utilises rasterio window read to minimise memory usage.

    Parameters
    ----------
    datafile : rasterio Datafile
        Any datafile that can be read by rasterio.
    shapefiles : GeoJSON
        GeoJSON file of AOI polygons, CRS = 4326.
    polygonIds : list
        List of unique ID values to filter shapefiles by.

    Returns
    -------
    df : pandas DataFrame
        Mean of each band for each AOI.

    '''
    plots = overlaps_flightline(datafile, shapefiles)
    custom_header = ''
    
    with rasterio.open(datafile) as img_rstr:
        bands = img_rstr.descriptions    
        
        Sampling = samples.copy()
        if type(samples[-1]) == dict:
            custom_header = samples[-1].get('custom')+'th%'
            Sampling[-1] = custom_header

        cols = [x.split(' ')[0]+'_'+a for a in Sampling for x in bands]
    
        df = pd.DataFrame(columns=cols,index=plots.plot_id)
              
        for shp in plots.plot_id:

            window = img_rstr.window(*plots[plots['plot_id']==shp].bounds.iloc[0])
            shapes = ((geom,value) for geom, value in zip(plots[plots['plot_id']==shp].geometry, plots[plots['plot_id']==shp].plot_id))

            rows,cols = img_rstr.read(int(img_rstr.count/2), window=from_bounds(*plots[plots['plot_id']==shp].bounds.iloc[0], transform=img_rstr.transform),boundless=True).shape
            result = rasterize(shapes=shapes,out_shape=(rows,cols),transform=img_rstr.window_transform(window))
            result_3d = np.repeat(result[np.newaxis,...],(img_rstr.count),0)        
            array = img_rstr.read(window=from_bounds(*plots[plots['plot_id']==shp].bounds.iloc[0], transform=img_rstr.transform))
            ary = np.ma.masked_where(result_3d!=shp,array)
            ary = np.ma.masked_where(ary==0,ary)
            
            if 'Mean' in Sampling:
                df.loc[shp, df.columns.str.contains('_Mean')] = np.ma.mean(ary,axis=(1,2))
            if 'Median' in Sampling:
                df.loc[shp, df.columns.str.contains('_Median')] = np.ma.median(ary, axis=(1,2))
            if 'Count' in Sampling:
                df.loc[shp, df.columns.str.contains('Count')] = np.ma.count(ary,axis=(1,2))
            if 'StDev' in Sampling:
                df.loc[shp, df.columns.str.contains('_StDev')] = np.ma.std(ary,axis=(1,2))
            if '99th%' in Sampling:
                df.loc[shp,df.columns.str.contains('_99th%')] = np.nanpercentile(ary.astype(float).filled(np.nan),99,axis=(1,2))
            if '90th%' in Sampling:
                df.loc[shp,df.columns.str.contains('_90th%')] = np.nanpercentile(ary.astype(float).filled(np.nan),90,axis=(1,2))
            if custom_header in Sampling:
                df.loc[shp,df.columns.str.contains(custom_header)] = np.nanpercentile(ary.astype(float).filled(np.nan),int(samples[-1].get('custom')),axis=(1,2))

            df.loc[shp,'Area'] = plots[plots['plot_id']==shp].Area.iloc[0]
            df.loc[shp,'SourceFile'] = os.path.basename(datafile)

    df.set_index([df.index,'Area','SourceFile'],inplace=True)
    
    return df

def hyperspec_master(variables,layers):
    '''
    Sample the band mean and standard deviation of hyperspec data from VNIR and/or SWIR sensors for AOIs defined by shapefiles.
    
    Save results to outfile CSV file.

    Parameters
    ----------
    variables : dict.
        Dictionary of variables required to process Hyperspectral data - outfile and shapefile
    layers : dict.
        Dictionary of layers to be processed e.g. VNIR and/or SWIR.

    Returns
    -------
    None.

    '''
    orthos=[]
    print('gere1')
    for layer in layers:
        if layers[layer] == 'blank' or layers[layer] == '':
            print ('no '+ layer)
        else:
            orthos.append(layer)            
    print('here')


    if 'VNIR' in orthos:
        try:
            vnir=[]
            files = [a for a in re.split("'|,",layers['VNIR']) if os.path.isfile(a)]
            for file in files:
                df = extract_hyperspec(file, variables['shapefile'],variables['samples'])
                print(f'{file} processed')
                vnir.append(df)
                
            vnir_all = pd.concat(vnir)
            vnir_all.sort_index().to_csv(variables['outfile_vnir'],index_label=['Plot_id','Area','SourceFile'])
        
        except Exception as e:
            print(e)
            
    if 'SWIR' in orthos:
        try:
            swir=[]
            files = [a for a in re.split("'|,",layers['SWIR']) if os.path.isfile(a)]
            for file in re.split("'|,",layers['SWIR']):
                if os.path.isfile(file):
                    df = extract_hyperspec(file,variables['shapefile'],variables['samples'])
                    print(f'{file} processed')
                    swir.append(df)
    
            swir_all = pd.concat(swir)
            swir_all.sort_index().to_csv(variables['outfile_swir'],index_label=['Plot_id','Area','SourceFile'])
        except Exception as e:
            print(e)
    
    print('Saving outputs...')
    print('Done')
