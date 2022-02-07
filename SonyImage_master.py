# -*- coding: utf-8 -*-
"""
Created on Thu Nov 25 10:22:12 2021

@author: holmanf
"""
from Vignetting_Modeller import *
from Exposure_Corrections import *
from Irradiance_Corrections import *
import subprocess
import os, sys, re
import shutil

class SonyMaster():
    def __init__(self):
        print('Lets begin...')

    def find_file(self, path, extention):
        '''
        Return list of files in folder which match file extention.
    
        Parameters
        ----------
        path : str
            Target folder path.
        extention : str
            Target file extention to filter files by.
    
        Returns
        -------
        results : list
            list of full file paths.
    
        '''
        results=[]
        for file in glob.glob(path+'*.'+extention):
            results.append(os.path.join(path,file))
        return (results)
    
    def move_images(self, source,destination):
        '''
        Move *tiff files from source to destination folder.
    
        Parameters
        ----------
        source : str
            Source folder path.
        destination : str
            Target destination folder path.
    
        Returns
        -------
        None.
    
        '''
        if os.path.exists(destination):
            None
        else:
            os.mkdir(destination)
        for im in self.find_file(source,'tiff'):
            shutil.move(os.path.join(source,im),os.path.join(destination,os.path.split(im)[1]))
        return
    
    def exif_corrector(self, infolder,outfolder):
        '''
        Utilising ExifTool, copy exif data from original .ARW images to final calibrated .tiff images.
    
        Parameters
        ----------
        infolder : str
            Source folder path containing .ARW images.
        outfolder : str
            Target folder path containing .tiff images.
    
        Returns
        -------
        None.
    
        '''
        for image in self.find_file(outfolder,'tiff'):
                raw_img= os.path.join(infolder,(re.split('([\\\/])',image)[-1].split('.')[0]+'.ARW'))
                exiftool=resource_path('exiftool.exe')
                exiftool_params=['%s'%exiftool,'-TagsFromFile','%s'%raw_img,'--Orientation','-author=FHolman','-overwrite_original','%s'%image]
                subprocess.run(exiftool_params)
                
    def correct_images(self, infolder,outfolder,vigfolder,t5file,camera,average):
        '''
        Apply the different calibration (ISO, aperture, shutter, vignetting, irradiance) steps to the Sony Images and save.
    
        Parameters
        ----------
        infolder : str
            Folder path to source .ARW imagery.
        outfolder : str
            Target folder path to save imagery.
        vigfolder : str
            Folder path to location of vingetting model images.
        t5file : str
            File path to Tec5 irradiance data file.
        camera : str
            String denoting which camera is being processed, NIR or RGB.
        average : str
            String denoting if irradiance data should be averaged for flight.
    
        Returns
        -------
        None.
    
        '''
        for im in self.find_file(infolder,'tiff'):
            if camera =='NIR':            
                image=tiff.imread(im)[:,:,2]            
                name=(im.replace('.','/'))
                indx=[i for i, elem in enumerate(name.split('/')) if 'DSC' in elem]
                name=name.split('/')[indx[0]]
                
                c1= image/iso_correction(im)
                c2=c1/aperture_correction(im)
                c3=c2*shutter_correction(im)
                c4=c3*vignetting_corretion(im,vigfolder,camera)   
                c5=c4/irradiance_correction(im,t5file,camera,average) 
                c6=0.0214*c5-0.0053
                c7=(c6).astype(np.float16)
                tiff.imsave(im,c7)
                
            if camera =='RGB':            
                r=tiff.imread(im)[:,:,0]
                g=tiff.imread(im)[:,:,1]
                b=tiff.imread(im)[:,:,2]
                name=(im.replace('.','/'))
                indx=[i for i, elem in enumerate(name.split('/')) if 'DSC' in elem]
                name=name.split('/')[indx[0]]
                
                r1=r/iso_correction(im)
                r2=r1/aperture_correction(im)
                r3=r2*shutter_correction(im)
                r4=r3*(vignetting_corretion(im,vigfolder,camera)[:,:,0])
                r5=r4/irradiance_correction(im,t5file,'R',average) 
                r6=0.0189*r5-0.00169
                
                g1=g/iso_correction(im)
                g2=g1/aperture_correction(im)
                g3=g2*shutter_correction(im)
                g4=g3*(vignetting_corretion(im,vigfolder,camera)[:,:,1])
                g5=g4/irradiance_correction(im,t5file,'G',average) 
                g6=0.00746*g5-0.00478
                
                b1=b/iso_correction(im)
                b2=b1/aperture_correction(im)
                b3=b2*shutter_correction(im)
                b4=b3*(vignetting_corretion(im,vigfolder,camera)[:,:,2])
                b5=b4/irradiance_correction(im,t5file,'B',average) 
                b6=0.01*b5-0.00285
                
                c6=np.dstack([r6,g6,b6]) # reform 3 channel RGB image
                c7=(c6).astype(np.float16)
                tiff.imsave(im,c7)
                
    def SonyImage_Master(self, variables):
        '''
        Master function for processing Sony raw images to calibrated reflectance image files (*.tiff).
    
        Parameters
        ----------
        variables : dict
            Dictionary of all inputs, namely; infodler, outfolder, vignetting folder, camera type, tec5 file.
    
        Returns
        -------
        None.
    
        '''
        from GUI_Master import resource_path
        print(variables)
        
        infolder=variables['infolder']
        outfolder=variables['outfolder']
        vigdest=variables['vigdest']
        camera=variables['camera']
        t5file=variables['t5file']
        average=variables['average']
        
        print('Converting Raw Imagery')
        print(infolder)
        for image in self.find_file(infolder,'ARW'):
            print('\tConverting '+image)
            darkim=resource_path('Dark_images/'+camera+'_Dark.pgm')
            dcraw=resource_path('dcraw64.exe')
            print(dcraw)
            dcraw_params=['%s'%dcraw,'-6','-W','-g','1','1','-T','-q','0','-o','0','-r','1','1','1','1','-t','0','-K','%s'%darkim,'%s'%image ]
            subprocess.run(dcraw_params)
            self.move_images(infolder,outfolder)
        print ('Raw conversion complete')
            
        print ('Generating vignetting filters')
        vigmodeller(outfolder,vigdest,camera)
        print ('Vignetting Complete')
            
        print('Correcting Images')
        self.correct_images(outfolder,outfolder,vigdest,t5file,camera,average)
        self.exif_corrector(infolder,outfolder)
        print('Done')
       
        