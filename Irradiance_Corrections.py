# -*- coding: utf-8 -*-
"""
Created on Fri Oct 19 10:36:39 2018

@author: fenner.holman@kcl.ac.uk

"""
import numpy as np
import pandas as pd
import exifread
from datetime import datetime

def irradiance_correction(image,tec5file,band,average):
    '''
    Calculates irradiance correction based on matching timestamps from images and irradiance dataset.
    
    If Average is specified, will average irradiance data for entire flight time period.
    
    If no Tec5 file specified, default correction factor will be returned.

    Parameters
    ----------
    image : str
        File path for image being processed.
    tec5file : str
        File path to Tec5 irradiance data.
    band : str
        String denoting specific band being processed, e.g. Red, Green, Blue etc.
    average : str
        Binary indicator (0,1) denoting if irradiance is to be averaged or not.

    Returns
    -------
    cf : float
        Irradiance correction value for specific image and band (float).

    '''

    if tec5file=='blank':
        print('WARNING!: No Irradiance data, final results will not be calibrated to reflectance.')
        cf=10000
        return (cf)
    else:
        tags=exifread.process_file(open(image,'rb'),details=False)
        imagetime=(str(tags['Image DateTime']))
        imagetime=datetime.strptime(imagetime, '%Y:%m:%d %H:%M:%S')
        irradiance=extract_downwelling(tec5file,band)
        irradiance['Time']=irradiance.index
        t1=imagetime-irradiance['Time']
        t1=t1/np.timedelta64(1,'s')
        index2=np.abs(t1).idxmin()
        
        if int(average)==1:
            cf=np.mean(irradiance['mean'])        
        else:
            cf=(irradiance.loc[index2,'mean'])
        print(imagetime,irradiance.loc[index2,'Time'],cf)
        
        return (cf)

    """Calculates downwelling correction for each camera band.
    Resamples irradiance data to 1 second before calucalting weighted average of irradiance based on specific camera spectral responses.
    """    

def extract_downwelling(tec5file,band):
    '''
    Calculate Tec5 irradiance measurements, weighted to Sony spectral responses.

    Parameters
    ----------
    tec5file : str
        File path to Tec5 irradiance data file.
    band : str
        String denoting specific band to be processed.

    Returns
    -------
    solar*band* : pandas DataFrame
        Band specific dataframe of weighted Tec5 irradiance.

    '''

    dateparser = lambda x: pd.to_datetime(x, dayfirst=True)
    raw = pd.read_excel(tec5file,parse_dates=['Timestamp:'],date_parser=dateparser,header=0)
    raw.columns=raw.columns.astype(str)
    temp = pd.DatetimeIndex(raw['Timestamp:'])
    raw['Timestamp:'] = temp    
    downwelling=(raw.loc[:,'360':'1000'][1::2]).reset_index(drop=True)
    timestamp=(raw['Timestamp:'][0::2]).reset_index(drop=True)
    inttime=(raw['Inttime:'][0::2]).reset_index(drop=True)        
    frame=[inttime,timestamp,downwelling]
    data=pd.concat(frame,axis=1).set_index('Timestamp:')
    data=(data.resample('1s')).interpolate(method='linear')    
    data['cf']=125/data['Inttime:']   
    data.loc[:,'360':'1000']=data.loc[:,'360':'1000'].multiply(data['cf'],axis='index')
    data['Inttime:']=data['Inttime:'].multiply(data['cf'],axis='index')
    
    if band =='NIR':
        solarNIR=(data.loc[:,'790':'980']).copy()
        solarNIR['790']=solarNIR['790']*0.134412538
        solarNIR['800']=solarNIR['800']*0.343003569
        solarNIR['810']=solarNIR['810']*0.591810039
        solarNIR['820']=solarNIR['820']*0.826681791
        solarNIR['830']=solarNIR['830']*0.983628958
        solarNIR['840']=solarNIR['840']*0.9918311
        solarNIR['850']=solarNIR['850']*0.924953321
        solarNIR['860']=solarNIR['860']*0.83827032
        solarNIR['870']=solarNIR['870']*0.741738829
        solarNIR['880']=solarNIR['880']*0.65335716
        solarNIR['890']=solarNIR['890']*0.556083735
        solarNIR['900']=solarNIR['900']*0.467502857
        solarNIR['910']=solarNIR['910']*0.395747503
        solarNIR['920']=solarNIR['920']*0.348254909
        solarNIR['930']=solarNIR['930']*0.297431716
        solarNIR['940']=solarNIR['940']*0.247413834
        solarNIR['950']=solarNIR['950']*0.20840349
        solarNIR['960']=solarNIR['960']*0.175523827
        solarNIR['970']=solarNIR['970']*0.141508061
        solarNIR['980']=solarNIR['980']*0.113592615
        solarNIR['mean']=(solarNIR.loc[:,'790':'980'].sum(axis=1))/9.981150174       
        
        return (solarNIR)
        
    if band =='R':
        solarR=data.loc[:,'580':'660'].copy()
        solarR['580']=solarR['580']*0.361666125
        solarR['590']=solarR['590']*0.595259799
        solarR['600']=solarR['600']*0.542917147
        solarR['610']=solarR['610']*0.461540899
        solarR['620']=solarR['620']*0.359283579
        solarR['630']=solarR['630']*0.281716312
        solarR['640']=solarR['640']*0.213550737
        solarR['650']=solarR['650']*0.158404844
        solarR['660']=solarR['660']*0.106596546        
        solarR['mean']=(solarR.loc[:,'580':'660'].sum(axis=1))/3.080935987
        
        return (solarR)
        
    if band =='G':   
        solarG=data.loc[:,'420':'610'].copy()        
        solarG['420']=solarG['420']*0.111829677
        solarG['430']=solarG['430']*0.135515749
        solarG['440']=solarG['440']*0.174619421
        solarG['450']=solarG['450']*0.215431166
        solarG['460']=solarG['460']*0.276531191
        solarG['470']=solarG['470']*0.40840359
        solarG['480']=solarG['480']*0.508973291
        solarG['490']=solarG['490']*0.550496635
        solarG['500']=solarG['500']*0.676022729
        solarG['510']=solarG['510']*0.843476019
        solarG['520']=solarG['520']*0.969532102
        solarG['530']=solarG['530']*1
        solarG['540']=solarG['540']*0.972092462
        solarG['550']=solarG['550']*0.920495099
        solarG['560']=solarG['560']*0.818098638
        solarG['570']=solarG['570']*0.703055324
        solarG['580']=solarG['580']*0.588220212
        solarG['590']=solarG['590']*0.448197493
        solarG['600']=solarG['600']*0.296833642
        solarG['610']=solarG['610']*0.176340962               
        solarG['mean']=(solarG.loc[:,'420':'610'].sum(axis=1))/10.7941654
        
        return (solarG)
        
    if band =='B':
        solarB=data.loc[:,'410':'540'].copy()        
        solarB['410']=solarB['410']*0.407531095
        solarB['420']=solarB['420']*0.505575531
        solarB['430']=solarB['430']*0.603085244
        solarB['440']=solarB['440']*0.721656421
        solarB['450']=solarB['450']*0.799857935
        solarB['460']=solarB['460']*0.83348627
        solarB['470']=solarB['470']*0.847330757
        solarB['480']=solarB['480']*0.793002725
        solarB['490']=solarB['490']*0.671136599
        solarB['500']=solarB['500']*0.510200752
        solarB['510']=solarB['510']*0.362844299
        solarB['520']=solarB['520']*0.235733559
        solarB['530']=solarB['530']*0.158060682
        solarB['540']=solarB['540']*0.113429487        
        solarB['mean']=(solarB.loc[:,'410':'540'].sum(axis=1))/7.562931355
        
        return (solarB)
    
