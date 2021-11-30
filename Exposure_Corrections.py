# -*- coding: utf-8 -*-
"""
Created on Fri Oct 19 10:47:56 2018

@author: fenner.holman@kcl.ac.uk


"""
import numpy as np
import exifread


def aperture_correction(image):
    '''
    Calculate aperture correction factor to normalise to f1 aperture. Correction factor = 1/(fnumber)^2

    Parameters
    ----------
    image : str
        File path for image to be processed.

    Returns
    -------
    correction : float.
        Aperture Correction Factor (float).

    '''
    tags=exifread.process_file(open(image,'rb'),details=False)
    
    while True:
        fn=(str(tags['EXIF FNumber']))
        try:
            top, bottom=fn.split('/')
            fnumber=(int(top)/int(bottom))
            fnumber=np.round(fnumber,2)
            break
        except ValueError:
            fnumber=int(fn)
            break
    correction=1/(fnumber**2)
    
    return (correction)

def iso_correction(image):
    '''
    Calculate ISO correction factor to normalise to ISO 100. Correction factor = ISO/100

    Parameters
    ----------
    image : str
        File path for image to be processed.

    Returns
    -------
    isoC : float.
        ISO Correction Factor (float).

    '''

    tags=exifread.process_file(open(image,'rb'),details=False)
    
    iso=(str(tags['EXIF ISOSpeedRatings']))
    isoc=int(iso)/100
    
    return (isoc)

def shutter_correction(image):
    '''
    Calculate shutter speed correction factor to normalise to a speed of 1/500. Correction factor = Shutter Speed/500

    Parameters
    ----------
    image : str
        File path for image to be processed.

    Returns
    -------
    shutC : float.
        Shutter Speed Correction Factor (float).

    '''

    tags=exifread.process_file(open(image,'rb'),details=False)
    
    while True:
        shutter=(str(tags['EXIF ExposureTime']))
        try:
            top, bottom=shutter.split('/')
            shutC=((int(bottom)/int(top))/500)
            break
        except ValueError:
            shutC=int(shutter)/500
            break
        
    return (shutC)