# -*- coding: utf-8 -*-
"""
Created on Fri Oct 19 10:43:21 2018

@author: fenner.holman@kcl.ac.uk
"""

import tifffile as tiff
import numpy as np
import os, re
import glob
import exifread
import math

def createCircularMask(h, w, center=None, radius=None):
    '''
    Generate circular masks based on image height and width

    Parameters
    ----------
    h : int
        Image height.
    w : int
        Image width.
    center : int, optional
        Image center coordinates, if known. The default is None.
    radius : int, optional
        Radius for circular mask. The default is None.

    Returns
    -------
    mask : TYPE
        DESCRIPTION.

    '''

    if center is None: # use the middle of the image
        center = [int(w/2), int(h/2)]
    if radius is None: # use the smallest distance between the center and image walls
        radius = min(center[0], center[1], w-center[0], h-center[1])
    Y, X = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((X - center[0])**2 + (Y-center[1])**2)
    mask = dist_from_center <= radius
    
    return (mask)

def createRingMask(h, w, center=None, InnerRadius=None, RingDiam=None):
    '''
    Generate rign mask of user defined size around the centre of an image.

    Parameters
    ----------
    h : int
        Image height.
    w : int
        Image width.
    center : int, optional
        Image center coordinates, if known. The default is None.
    InnerRadius : int, optional
        Radius of inner ring edge The default is None.
    RingDiam : int, optional
        Diameter of ring mask. The default is None.

    Returns
    -------
    mask : TYPE
        DESCRIPTION.

    '''

    if center is None: # use the middle of the image
        center = [int(w/2), int(h/2)]
    if InnerRadius is None: # use the smallest distance between the center and image walls
        radius = min(center[0], center[1], w-center[0], h-center[1])
    if RingDiam is None: #use 10
        RingDiam = radius + 10
    Y, X = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((X - center[0])**2 + (Y-center[1])**2)
    OuterRadius=InnerRadius + RingDiam
    mask = np.logical_and (InnerRadius <= dist_from_center, dist_from_center <= OuterRadius)    
    return (mask)

def myround(x, base):
    '''
    Round values to nearest whole number.

    Parameters
    ----------
    x : float
        Value to be rounded.
    base : int
        Base value.

    Returns
    -------
    int
        Rounded value.

    '''
    
    return (int(base * math.ceil(float(x)/base)))

def maxDiam(h,w, RingDiam):
    '''
    Calculate largest possible diameter based on image height and width.

    Parameters
    ----------
    h : int
        Image height.
    w : int
        Image width.
    RingDiam : int
        Diameter of ring mask.

    Returns
    -------
    maximum : int
        Maimum dimater value.

    '''
    
    diag=math.sqrt((h**2)+(w**2))
    maximum=myround(int(diag/2),RingDiam)
    return (maximum)   

def sort_images(folder):
    '''
    Return dictionary of images sorted by aperture value.

    Parameters
    ----------
    folder : str
        Folder path containing images.

    Returns
    -------
    fstop : dict
        Dictionary of all images, grouped by aperture.

    '''
    
    os.chdir(folder)
    fstop=[]
    for im in glob.glob('*.tiff'):
        tags=exifread.process_file(open(im,'rb'),details=False)   
        while True:
            fn=(str(tags['EXIF FNumber']))
            try:
                top, bottom=fn.split('/')
                fnumber=round((int(top)/int(bottom)),1)
                break
            except ValueError:
                fnumber=int(fn)
                break
        fstop.append(fnumber)
    fstop=list(dict.fromkeys(fstop))
    return (fstop)

def get_aperture(image):
    '''
    Extract aperture value (fnumber) from image file.

    Parameters
    ----------
    image : str
        Image file path.

    Returns
    -------
    fnumber : int
        Image aperture (f-number) value.

    '''
    
    tags=exifread.process_file(open(image,'rb'),details=False)
    while True:
        fn=(str(tags['EXIF FNumber']))
        try:
            top, bottom=fn.split('/')
            fnumber=(int(top)/int(bottom))
            fnumber=np.round(fnumber,2)
            
        except ValueError:
            fnumber=int(fn)
            
    return (fnumber)

def get_ISO(image):
    '''
    Extracts ISO value from image file.

    Parameters
    ----------
    image : str
        Image file path.

    Returns
    -------
    iso : int
        Image ISO value (integer).

    '''
    
    tags=exifread.process_file(open(image,'rb'),details=False)
    iso=(str(tags['EXIF ISOSpeedRatings']))
    
    return (int(iso))
    
def vignetting(vigfolder,camera):
    '''
    List all vignetting models within a specified folder.

    Parameters
    ----------
    vigfolder : str
        Vignetting folder path.
    camera : str
        String denoting which camera, RGB or NIR.

    Returns
    -------
    vigmodels : dict
        Dictionary of all vignetting models for targeted camera.

    '''
    
    os.chdir(vigfolder)
    vigmodels={}
    if camera =='NIR':
        for i in glob.glob('*NIR*.tif'):
            vigmodels[float(re.split('/',i.replace('_','/'))[0])]=os.path.join(vigfolder,i)
    if camera=='RGB':
        for i in glob.glob('*RGB*.tif'):
            vigmodels[float(re.split('/',i.replace('_','/'))[0])]=os.path.join(vigfolder,i)
    
    return (vigmodels)

def vignetting_corretion(image,vigfolder,camera):
    '''
    Identify and extract generated vignetting model frog iven image based on camera and aperture values.

    Parameters
    ----------
    image : str
        Image file path.
    vigfolder : str
        Vignetting folder path.
    camera : str
        String denoting which camera, RGB or NIR.

    Returns
    -------
    vigmodel : np.array
        Numpy array of image/aperture relevant vignetting model.

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
    vigmodel=(np.array(tiff.imread(vignetting(vigfolder,camera).get(fnumber))))
    
    return (vigmodel)  
    
def vigmodeller(infolder,outfolder,camera):
    '''
    Generates vignettting model from image set of consistent camera and aperture.
    
    Key steps are:
        1.Average all images
        2.Generate ring masks and calcualte median of each suquential ring
        3.Calculate 2nd degree polynomial on medians vs. distande from image centre
        4.Generate vigentting model by applying polynomial to each mask ring.
    

    Parameters
    ----------
    infolder : str
        Folder path of input images.
    outfolder : str
        Folder path to save vingetting models.
    camera : str
        String denotion of which camera is being processed, RGB or NIR.

    Returns
    -------
    None.

    '''

    if not os.path.exists(outfolder):
        os.makedirs(outfolder)
    os.chdir(infolder)
    for x in sort_images(infolder):
        if camera =='NIR':
            vig=np.empty([4024,6024])
            avrge=0    
            for im in glob.glob('*.tiff'):
                fnumber=get_aperture(im)        
                if fnumber == x:
                    with tiff.TiffFile(im)as tif:     
                        nir=tif.asarray()               
                        nir=nir[:,:,2]/(get_ISO(im)/100)
                        vig=vig+nir
                        avrge=avrge+1
            vig=vig[:,:]/avrge    
            biggest=maxDiam(4024,6024,25)
            median=[]
            distance=[]
            rad=0
            vigmodel=np.empty([4024,6024])    
            while rad < biggest:
                ring=createRingMask(4024,6024,InnerRadius=rad,RingDiam=25)
                mskedimg=vig.copy()
                median.append(np.median(mskedimg[ring]))   
                rad=rad+25
                distance.append(rad)        
            coefs=np.polyfit(distance,median,2)
            cf=np.polyval(coefs,distance)        
            while rad > 0:
                test=createCircularMask(4024,6024,radius=rad)    
                vigmodel[test]=(cf.max()/cf[int((rad/25)-1)])
                rad=rad-25
            vigmodel=vigmodel.astype(np.float16)
        if camera=='RGB':
            vigr=np.empty([4024,6024])
            vigg=np.empty([4024,6024])
            vigb=np.empty([4024,6024])
            avrge=0    
            for im in glob.glob('*.tiff'):
                fnumber=get_aperture(im)        
                if fnumber == x:
                    with tiff.TiffFile(im)as tif:     
                        array=tif.asarray()               
                        r=array[:,:,0]/(get_ISO(im)/100)
                        g=array[:,:,1]/(get_ISO(im)/100)
                        b=array[:,:,2]/(get_ISO(im)/100)
                        vigr=vigr+r
                        vigg=vigg+g
                        vigb=vigb+b
                        avrge=avrge+1
            vigr=vigr[:,:]/avrge
            vigg=vigg[:,:]/avrge
            vigb=vigb[:,:]/avrge    
            biggest=maxDiam(4024,6024,25)
            medianr=[]
            mediang=[]
            medianb=[]
            distance=[]
            rad=0
            vigmodelr=np.empty([4024,6024])
            vigmodelg=np.empty([4024,6024])
            vigmodelb=np.empty([4024,6024])    
            while rad < biggest:
                ring=createRingMask(4024,6024,InnerRadius=rad,RingDiam=25)
                mskedimgr=vigr.copy()
                medianr.append(np.median(mskedimgr[ring]))
                mskedimgg=vigg.copy()
                mediang.append(np.median(mskedimgg[ring]))
                mskedimgb=vigb.copy()
                medianb.append(np.median(mskedimgb[ring]))
                rad=rad+25
                distance.append(rad)        
                coefs=np.polyfit(distance,medianr,2)
                cfr=np.polyval(coefs,distance)
                coefs=np.polyfit(distance,mediang,2)
                cfg=np.polyval(coefs,distance)
                coefs=np.polyfit(distance,medianb,2)
                cfb=np.polyval(coefs,distance)   
            while rad > 0:
                test=createCircularMask(4024,6024,radius=rad)
                vigmodelr[test]=(cfr.max()/cfr[int((rad/25)-1)])
                vigmodelg[test]=(cfg.max()/cfg[int((rad/25)-1)])
                vigmodelb[test]=(cfb.max()/cfb[int((rad/25)-1)])
                rad=rad-25
            allcorrect=np.dstack([vigmodelr,vigmodelg,vigmodelb])
            vigmodel=allcorrect.astype(np.float32)
        
        
        tiff.imsave(outfolder+str(x)+'_'+camera+'_vigModel.tif',vigmodel)
    return