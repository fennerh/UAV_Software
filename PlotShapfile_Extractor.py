# -*- coding: utf-8 -*-
"""
Created on Fri Mar  2 11:45:23 2018

@author: k1333986
"""
"""
Script takes any shapefile containing multiple separate shapes and produces inidividual shapefiles for each one.
"""

import geopandas
import re

def shapefile_gen(Shapefile,out_file):
    '''
    Convert multipolygon shapefile to GeoJSON. 
    
    "Attempts" to capture variation plot ID column and rename it to 'plot_id' for consistency.

    Parameters
    ----------
    Shapefile : .shp file
        Shapefile of AOI polygons.
    out_file : file path
        Destination of generated GeoJSON file.

    Returns
    -------
    None.

    '''
    myshpfile = geopandas.read_file(Shapefile)
    myshpfile = myshpfile.to_crs("EPSG:4326")
    myshpfile.columns = [a.lower() for a in myshpfile.columns.to_list()]
    identifier = [b for b in myshpfile.columns if str(myshpfile[b].dtype) == 'int64' and myshpfile[b].max() == len(myshpfile)][0]
    myshpfile = myshpfile.rename(columns={identifier:'plot_id'})
    if myshpfile['plot_id'].max() != len(myshpfile['plot_id']):
        raise ValueError('Shapefile Plot_ID column invalid. Is it present and numbered?')
    elif out_file.split('.')[-1] == 'geojson':
        myshpfile.to_file(out_file, driver='GeoJSON')
    else:
        myshpfile.to_file(out_file+'.geojson', driver='GeoJSON')


