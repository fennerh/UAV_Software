# -*- coding: utf-8 -*-
"""
Created on Thu Nov 25 10:19:00 2021

@author: holmanf
"""

import os,sys
from typing_extensions import IntVar

## Defines current working directory even in executable.
def resource_path(relative_path):
    """ Get absolute path to resource, works for development and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

os.environ["GDAL_DATA"] = resource_path('gdal')
os.environ["PROJ_LIB"] = resource_path('proj')
os.environ["USE_PATH_FOR_GDAL_PYTHON"] = 'YES'
os.environ['PATH'] = os.pathsep.join(os.environ['PATH'].split(os.pathsep)[:-1])
print(os.environ["GDAL_DATA"])

abspath = os.path.abspath(__file__)
dname = (os.path.dirname(abspath))
os.chdir(dname)
print(dname)

import math
import time
import shutil
import exifread
import threading
import subprocess
import numpy as np
import glob, re
import pandas as pd
import tkinter as tk
import tifffile as tiff
import fiona
import geopandas
import cv2
import traceback
import xlsxwriter
import threading
import ctypes
import rasterio
import gc

from random import randint
from rasterio.mask import mask
from datetime import datetime
from osgeo import ogr, gdal
from shapely.geometry import shape, mapping
from ttkwidgets import tooltips
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import font
from tkinter import PhotoImage
from tkinter.ttk import Style
from ttkwidgets.autocomplete import AutocompleteCombobox
from queue import Queue
from SonyImage_master import SonyMaster
from PlotShapfile_Extractor import shapefile_gen
from Data_Extractor import hyperspec_master
from mergingSony import orthoMerge
from itertools import count
from PIL import ImageTk, Image
from natsort import natsorted

##Set DPI awareness to improve display##
ctypes.windll.shcore.SetProcessDpiAwareness(1)

## Define style variables for Tkinter##
Large_Font=("Verdana",12,'bold')
Norm_Font=("Verdana",10)
Small_font=("Verdana",8)

## Define text files for saving locations of shapefiles##
fieldfile=open(resource_path('Requirements\\fieldshapefile.txt'),'r+')
fieldshape=fieldfile.read()
file=open(resource_path('Requirements\\plotshapefiles.txt'),'r+')
shapefolder=file.read()
groundfile=open(resource_path('Requirements\\groundDEM.txt'),'r+')
grnddem=groundfile.read()

##Define Graphics file locations##
info_button = resource_path('Graphics\\button_info.png')
home_button = resource_path('Graphics\\button_home.png')
exit_button = resource_path('Graphics\\button_exit.png')
back_button = resource_path('Graphics\\button_back.png')
sony_button = resource_path('Graphics\\button_camera.png')
geojson_button = resource_path('Graphics\\button_shapefile.png')
spectrum_button = resource_path('Graphics\\button_extractor.png')
layers_button = resource_path('Graphics\\button_layers.png')

class ImageLabel(tk.Label):
    """a label that displays images, and plays them if they are gifs"""
    def load(self, im):
        if isinstance(im, str):
            im = Image.open(im)
        self.loc = 0
        self.frames = []

        try:
            for i in count(1):
                self.frames.append(ImageTk.PhotoImage(im.copy()))
                im.seek(i)
        except EOFError:
            pass

        try:
            self.delay = im.info['duration']
        except:
            self.delay = 100

        if len(self.frames) == 1:
            self.config(image=self.frames[0])
        else:
            self.next_frame()

    def unload(self):
        self.config(image="")
        self.frames = None

    def next_frame(self):
        if self.frames:
            self.loc += 1
            self.loc %= len(self.frames)
            self.config(image=self.frames[self.loc])
            self.after(self.delay, self.next_frame)

## Software Class: Defines the Tkinter variables for the GUI software.
class software(tk.Tk):
    def __init__(self,*args,**kwargs):
        tk.Tk.__init__(self,*args,**kwargs)
        # self.tk.call('tk', 'scaling', 3.0)
        tk.Tk.wm_title(self,"UAV Data Tool")

        container=tk.Frame(self)
        container.pack(side='top',fill='both',expand=True)
        container.grid_rowconfigure(0,weight=1)
        container.grid_columnconfigure(0,weight=1)

        self.frames={}
        for F in (HomePage,ImageCalibrator,batchcalibrator,Shapefilegenerator,HyperSpecExtractor,OrthoMerging): #DataMerger,DataExtractor
            frame=F(container,self)
            self.frames[F]=frame
            frame.grid(row=0,column=0,sticky='nsew')
        self.show_frame(HomePage)

    def show_frame(self,cont):
        frame=self.frames[cont]
        frame.tkraise()
    def enditall(self):
        global file
        file.close()
        self.destroy()

## Homepage Class: Defines the variables for the appearance and function of the software homepage.
class HomePage(ttk.Frame):
    def popup_window(self):
        win_x = self.winfo_rootx()+300
        win_y = self.winfo_rooty()+100
        window = tk.Toplevel()
        window.geometry(f'+{win_x}+{win_y}')
        window.title('UAV Data Tool - Help')

        label = tk.Label(window, text='''
        Image Calibration Tool: if you want to calibrate raw Sony imagery into reflectances.
        
        Shapefile Generator: if you want to process experiment shapefiles ready for data extraction.
                         ''',justify='left')
        label.pack(fill='x', padx=50, pady=50)

        button_close = ttk.Button(window, text="Close", command=window.destroy)
        button_close.pack(fill='x')
    def __init__(self,parent,controller):
               
        tk.Frame.__init__(self,parent)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.topframe = tk.Frame(self)
        self.midframe = tk.Frame(self)
        self.btmframe = tk.Frame(self)
        
        self.topframe.grid(row=0)
        self.midframe.grid(row=1)
        self.btmframe.grid(row=2)
        
        info_btn = PhotoImage(file=info_button,master=self).subsample(5,5)
        ext_btn = PhotoImage(file=exit_button,master=self).subsample(5,5)
        clb_btn = PhotoImage(file=sony_button,master=self).subsample(2,2)
        shp_btn = PhotoImage(file=geojson_button,master=self).subsample(2,2)
        spc_btn = PhotoImage(file=spectrum_button,master=self).subsample(2,2)
        lyr_btn = PhotoImage(file=layers_button,master=self).subsample(2,2)

        button1=ttk.Button(self.midframe,text='Image Calibration Tool',image=clb_btn,tooltip='Tool for calibrating Sony a6000 RAW imagery to calibrated reflectance' ,command=lambda: controller.show_frame(ImageCalibrator),compound='top')
        button1.image = clb_btn
        button1.grid(row=1,column=1,padx=15, pady=15)

        button2=ttk.Button(self.midframe,text='Ortho Merger',image=lyr_btn,tooltip='Tool for merging orthomosaics from different sensors',command=lambda: controller.show_frame(OrthoMerging),compound='top')
        button2.image = lyr_btn
        button2.grid(row=1,column=2,padx=15, pady=15)

        button4=ttk.Button(self.midframe,text='Shapefile Generator',image=shp_btn,tooltip='Tool for generating GeoJSON files from Area of Interest shapefiles',command=lambda: controller.show_frame(Shapefilegenerator),compound='top')
        button4.image = shp_btn
        button4.grid(row=2,column=1,padx=15, pady=15)
        
        button3=ttk.Button(self.midframe,text='Data Extractor',image=spc_btn,tooltip='Tool for extracting statstics from spatial datasets',command=lambda: controller.show_frame(HyperSpecExtractor),compound='top')
        button3.image = spc_btn
        button3.grid(row=2,column=2,padx=15, pady=15)
       
        button5=ttk.Button(self.btmframe,text='Quit',image=ext_btn,tooltip='Quit software and all running processes',command=controller.enditall,compound='top')
        button5.image=ext_btn
        button5.grid(row=1,column=3,padx=5,pady=10)
        
        button6=ttk.Button(self.btmframe,text='Help',image=info_btn,tooltip='Get additional help',command=self.popup_window,compound='top')
        button6.image=info_btn
        button6.grid(row=1,column=1,padx=5,pady=10)


## Image Calibrator Class: defines the variables for the appearance and function of the Image Calibration Tool.
class ImageCalibrator(ttk.Frame):
    
    def popup_window(self):
        win_x = self.winfo_rootx()+300
        win_y = self.winfo_rooty()+100
        window = tk.Toplevel()
        window.geometry(f'+{win_x}+{win_y}')
        window.title('Image Calibrator - Help')

        label = tk.Label(window, text='''
        Raw imagery = Folder containing sony .ARW image files from data capture flight
        
        Tec5 file = .xlsx file containing Tec5 irradiance data from data capture flight
        
        Average Irradiance = Select to use single meaned irradiance value for relfectance corrections
        
        Vignetting Models = Destination folder for band vignetting models produced during processing
        
        Out folder = Destination folder for calibrated .tiff imagery''',justify='left')
        label.pack(fill='x', padx=50, pady=50)

        button_close = ttk.Button(window, text="Close", command=window.destroy)
        button_close.pack(fill='x')
    

    def get_raw(self):
        self.button5.configure(state='enabled')
        folder=tk.filedialog.askdirectory(initialdir = "/",title = 'Select Raw Folder')
        self.rawfolder.set(folder+'/')
        try:
            self.t5file.set((glob.glob(os.path.abspath(os.path.join(self.rawfolder.get(),'../'))+'/'+'*ec5*'+'*.xlsx'))[0])
        except:
            tk.messagebox.showwarning(title='Warning',message='No Tec5 File found')
            self.t5file.set('blank')
        self.vigfolder.set(os.path.join(os.path.abspath(os.path.join(self.rawfolder.get(),"../")+'VIG_models\\'),''))
        try:
            self.cam.set(re.split('/',self.rawfolder.get())[re.split('/',self.rawfolder.get()).index('NIR')])
            self.outfolder.set(os.path.join(os.path.abspath(os.path.join(self.rawfolder.get(),"../")+(re.split('/',self.rawfolder.get())[re.split('/',self.rawfolder.get()).index('NIR')])+'_AllCorrect'),''))
        except:
            self.cam.set(re.split('/',self.rawfolder.get())[re.split('/',self.rawfolder.get()).index('RGB')])
            self.outfolder.set(os.path.join(os.path.abspath(os.path.join(self.rawfolder.get(),"../")+(re.split('/',self.rawfolder.get())[re.split('/',self.rawfolder.get()).index('RGB')])+'_AllCorrect'),''))

    def get_t5(self):
        try:
            folder=tk.filedialog.askopenfilename(initialdir = os.path.abspath(os.path.join(self.rawfolder.get() ,"../")),title = 'Select Tec5 File',filetypes = (("excel files","*.xlsx"),("all files","*.*")))
            self.t5file.set(folder)
        except:
            tk.messagebox.showwarning(title='Warning',message='No Tec5 File found')
            self.t5file.set('blank')
        
    def get_vig(self):
        folder=tk.filedialog.askdirectory(initialdir = os.path.abspath(os.path.join(self.rawfolder.get() ,"../")),title = 'Select Vignette Model Folder')
        self.vigfolder.set(folder+'/')

    def get_out(self):
        folder=tk.filedialog.askdirectory(initialdir = os.path.abspath(os.path.join(self.rawfolder.get() ,"../")),title = 'Select Output Folder')
        self.outfolder.set(folder+'/')

    def _toggle_state(self, state):
        state = state if state in ('normal', 'disabled') else 'normal'
        widgets = (self.button1, self.button2,self.button3,self.button4,self.button5,self.rgb,self.button8,self.button9,self.button10)
        for widget in widgets:
            widget.configure(state=state)

    def monitor(self, thread):
        if thread.is_alive():
            # check the thread every 100ms
            self.after(100, lambda: self.monitor(thread))
        else:
            tk.messagebox.showinfo("Processing Complete", "Processing Complete")
            gc.collect()
            self._toggle_state('enabled')

    def click_run(self):
        self._toggle_state('disabled')
        try:
            variables={'infolder':self.rawfolder.get(),'outfolder':self.outfolder.get(),'t5file':self.t5file.get(),'vigdest':self.vigfolder.get(),'camera':self.cam.get(),'average':self.average.get()}
            gc.collect()
            thread_1 = threading.Thread(target=SonyMaster().SonyImage_Master(variables))
            thread_1.setDaemon(True)
            thread_1.start()
            
            self.monitor(thread_1)
        
        except Exception as e:
            tk.messagebox.showerror("Error", e)
            traceback.print_exc()
            self._toggle_state('normal')

    def __init__(self,parent,controller):
            tk.Frame.__init__(self,parent)
            self.grid_rowconfigure(1, weight=1)
            self.grid_columnconfigure(0, weight=1)

            self.topframe = tk.Frame(self)
            self.midframe = tk.Frame(self)
            self.btmframe = tk.Frame(self)
            
            self.topframe.grid(row=0)
            self.midframe.grid(row=1)
            self.btmframe.grid(row=2)

            #---VARIABLES---#
            self.rawfolder=tk.StringVar()
            self.t5file=tk.StringVar()
            self.vigfolder=tk.StringVar()
            self.outfolder=tk.StringVar()
            self.cam=tk.StringVar()
            self.queue=Queue()
            options=['Please Select*','NIR','RGB']
            self.batch=[]
            self.average=tk.IntVar()
            info_btn = PhotoImage(file=info_button,master=self).subsample(5,5)
            hme_btn = PhotoImage(file=home_button,master=self).subsample(5,5)
            ext_btn = PhotoImage(file=exit_button,master=self).subsample(5,5)

            #---LABELS---#
            self.label=tk.Label(self.topframe,text='Image Calibration',font=Large_Font)
            self.label.grid(row=0,column=2,padx=10)
            
            self.label=tk.Label(self.topframe,font=Norm_Font,
                                text='Calibrate raw (.ARW) sony images to reflectance (%).')
            self.label.grid(row=1,column=2,padx=10)

            #---BUTTONS---#
            self.button1=ttk.Button(self.midframe,text='Raw Imagery',command=self.get_raw,width=20)
            self.button1.grid(row=3,column=1,pady=5)

            self.button2=ttk.Button(self.midframe,text='Tec5 File',command=self.get_t5,width=20)
            self.button2.grid(row=4,column=1,pady=5)

            self.button3=ttk.Button(self.midframe,text='Vignetting Models',command=self.get_vig,width=20)
            self.button3.grid(row=5,column=1,pady=5)

            self.button4=ttk.Button(self.midframe,text='Out Folder',command=self.get_out,width=20)
            self.button4.grid(row=6,column=1,pady=5)

            self.rgb=ttk.OptionMenu(self.midframe,self.cam,*options)
            self.rgb.grid(row=7,column=2,pady=5)

            self.button5=ttk.Button(self.midframe,text='Run',command=self.click_run)
            self.button5.configure(state='disabled')
            self.button5.grid(row=8,column=2,pady=10)

            self.button6=ttk.Button(self.midframe,text='Batch Processor',command=lambda: controller.show_frame(batchcalibrator))
            self.button6.configure(state='enabled')
            self.button6.grid(row=9,column=2)

            self.button7=ttk.Checkbutton(self.midframe,text='Average Irradiance',variable=self.average)
            self.button7.grid(row=4,column=3)

            self.button8=ttk.Button(self.btmframe,image=hme_btn,text='Home',tooltip='Go Home (your drunk)',command=lambda: controller.show_frame(HomePage),compound="top")
            self.button8.image=hme_btn 
            self.button8.grid(row=1,column=1,padx=5,pady=10)
    
            self.button9=ttk.Button(self.btmframe,image=info_btn,text='Help',command=self.popup_window,tooltip='Press for more help',compound="top")
            self.button9.image=info_btn  
            self.button9.grid(row=1,column=2,padx=5,pady=10)
    
            self.button10=ttk.Button(self.btmframe,text='Quit',image=ext_btn,tooltip='Quit software and all running processes',command=controller.enditall,compound="top")
            self.button10.image=ext_btn 
            self.button10.grid(row=1,column=3,padx=5,pady=10)

            #---ENTRIES---#
            self.entry1=ttk.Entry(self.midframe,textvariable=self.rawfolder,width=75)
            self.entry1.grid(row=3,column=2,padx=5)
            self.entry2=ttk.Entry(self.midframe,textvariable=self.t5file,width=75)
            self.entry2.grid(row=4,column=2,padx=5)
            self.entry3=ttk.Entry(self.midframe,textvariable=self.vigfolder,width=75)
            self.entry3.grid(row=5,column=2,padx=5)
            self.entry4=ttk.Entry(self.midframe,textvariable=self.outfolder,width=75)
            self.entry4.grid(row=6,column=2,padx=5)

## Image Calibrator Class: defines the variables for the appearance and function of the Batch Processing Image Calibration Tool.
class batchcalibrator(ttk.Frame):
    def popup_window(self):
        win_x = self.winfo_rootx()+300
        win_y = self.winfo_rooty()+100
        window = tk.Toplevel()
        window.geometry(f'+{win_x}+{win_y}')
        window.title('Batch Calibrator - Help')

        label = tk.Label(window, text='''
        Raw imagery = Folder containing sony .ARW image files from data capture flight
        
        Tec5 file = .xlsx file containing Tec5 irradiance data from data capture flight
        
        Average Irradiance = Select to use single meaned irradiance value for relfectance corrections
        
        Vignetting Models = Destination folder for band vignetting models produced during processing
        
        Out folder = Destination folder for calibrated .tiff imagery
        
        Add/Delete = add or remove the current dataset to the batch processing queue
        ''',justify='left')
        label.pack(fill='x', padx=50, pady=50)

        button_close = ttk.Button(window, text="Close", command=window.destroy)
        button_close.pack(fill='x')

    def get_raw(self):
        self.button5.configure(state='enabled')
        folder=tk.filedialog.askdirectory(initialdir = "/",title = 'Select Raw Folder')
        self.rawfolder.set(folder+'/')
        try:
            self.t5file.set((glob.glob(os.path.abspath(os.path.join(self.rawfolder.get(),'../'))+'/'+'*ec5*'+'*.xlsx'))[0])
        except:
            tk.messagebox.showinfo('Error','No Tec5 file found')
            self.t5file.set('blank')
        self.vigfolder.set(os.path.join(os.path.abspath(os.path.join(self.rawfolder.get(),"../")+'VIG_models\\'),''))
        try:
            self.cam.set(re.split('/',self.rawfolder.get())[re.split('/',self.rawfolder.get()).index('NIR')])
            self.outfolder.set(os.path.join(os.path.abspath(os.path.join(self.rawfolder.get(),"../")+(re.split('/',self.rawfolder.get())[re.split('/',self.rawfolder.get()).index('NIR')])+'_AllCorrect'),''))
        except:
            self.cam.set(re.split('/',self.rawfolder.get())[re.split('/',self.rawfolder.get()).index('RGB')])
            self.outfolder.set(os.path.join(os.path.abspath(os.path.join(self.rawfolder.get(),"../")+(re.split('/',self.rawfolder.get())[re.split('/',self.rawfolder.get()).index('RGB')])+'_AllCorrect'),''))

    def get_t5(self):
        try:
            folder=tk.filedialog.askopenfilename(initialdir = os.path.abspath(os.path.join(self.rawfolder.get() ,"../")),title = 'Select Tec5 File',filetypes = (("excel files","*.xlsx"),("all files","*.*")))
            self.t5file.set(folder)
        except:
            tk.messagebox.showinfo('Error','No Tec5 file found')
            self.t5file.set('blank')

    def get_vig(self):
        folder=tk.filedialog.askdirectory(initialdir = os.path.abspath(os.path.join(self.rawfolder.get() ,"../")),title = 'Select Vignette Model Folder')
        self.vigfolder.set(folder+'/')

    def get_out(self):
        folder=tk.filedialog.askdirectory(initialdir = os.path.abspath(os.path.join(self.rawfolder.get() ,"../")),title = 'Select Output Folder')
        self.outfolder.set(folder+'/')

    def add2batch(self):
        batch_vars={'infolder':self.rawfolder.get(),'outfolder':self.outfolder.get(),'t5file':self.t5file.get(),'vigdest':self.vigfolder.get(),'camera':self.cam.get(),'average':self.average.get()}
        self.batch.append(batch_vars)
        self.batchbox.insert('end',str(batch_vars))
        self.button9.configure(state='enabled')

    def deletebatch(self):
        self.batch.pop(-1)
        self.batchbox.delete('1.0','end')
        self.batchbox.insert('end',self.batch)

    def _toggle_state(self, state):
        state = state if state in ('normal', 'disabled') else 'normal'
        widgets = (self.button1, self.button2,self.button3,self.button4,self.button5,self.rgb,self.button8,self.button9,self.button10)
        for widget in widgets:
            widget.configure(state=state)
            
    def monitor(self, thread):
        if thread.is_alive():
            # check the thread every 100ms
            self.after(100, lambda: self.monitor(thread))
        else:
            tk.messagebox.showinfo("Processing Complete", "Processing Complete")
            gc.collect()
            self._toggle_state('enabled')

    def batchrun(self):
        self._toggle_state('disabled')
    
        for batch in self.batch:
            print(batch)
            gc.collect()
            thread_1 = threading.Thread(target=SonyMaster().SonyImage_Master(batch))
            thread_1.setDaemon(True)
            thread_1.start()
            
            self.monitor(thread_1)

    def __init__(self,parent,controller):
        tk.Frame.__init__(self,parent)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.topframe = tk.Frame(self)
        self.midframe = tk.Frame(self)
        self.btmframe = tk.Frame(self)
        
        self.topframe.grid(row=0)
        self.midframe.grid(row=1)
        self.btmframe.grid(row=2)

        #---VARIABLES---#
        self.rawfolder=tk.StringVar()
        self.t5file=tk.StringVar()
        self.vigfolder=tk.StringVar()
        self.outfolder=tk.StringVar()
        self.cam=tk.StringVar()
        self.queue=Queue()
        options=['Please Select*','NIR','RGB']
        self.batch=[]
        self.average=tk.IntVar()
        info_btn = PhotoImage(file=info_button,master=self).subsample(5,5)
        hme_btn = PhotoImage(file=home_button,master=self).subsample(5,5)
        ext_btn = PhotoImage(file=exit_button,master=self).subsample(5,5)
        bck_btn = PhotoImage(file=back_button,master=self).subsample(5,5)

        #---LABELS---#
        self.label=tk.Label(self.topframe,text='Image Calibration',font=Large_Font)
        self.label.grid(row=0,column=2,padx=10)
        
        self.label1=tk.Label(self.topframe,font=Norm_Font,
                            text='Calibrate raw (.ARW) sony images to reflectance (%), but now in batches!')
        self.label1.grid(row=1,column=2,padx=10)

        #---BUTTONS---#
        self.button1=ttk.Button(self.midframe,text='Raw Imagery',command=self.get_raw,width=20)
        self.button1.grid(row=1,column=1,pady=5)

        self.button2=ttk.Button(self.midframe,text='Tec5 File',command=self.get_t5,width=20)
        self.button2.grid(row=2,column=1,pady=5)

        self.button3=ttk.Button(self.midframe,text='Vignetting Models',command=self.get_vig,width=20)
        self.button3.grid(row=3,column=1,pady=5)

        self.button4=ttk.Button(self.midframe,text='Out Folder',command=self.get_out,width=20)
        self.button4.grid(row=4,column=1,pady=5)

        self.rgb=ttk.OptionMenu(self.midframe,self.cam,*options)
        self.rgb.grid(row=5,column=2,pady=5,columnspan=2)

        self.button5=ttk.Button(self.midframe,text='Batch Run',command=self.batchrun)
        self.button5.configure(state='disabled')
        self.button5.grid(row=9,column=2,columnspan=2)

        self.button7=ttk.Button(self.midframe,text='Add',command=self.add2batch)
        self.button7.grid(row=6,column=2,sticky='e')

        self.button17=ttk.Button(self.midframe,text='Delete',command=self.deletebatch)
        self.button17.grid(row=6,column=3,sticky='w')
        
        self.button27=ttk.Checkbutton(self.midframe,text='Average Irradiance',variable=self.average)
        self.button27.grid(row=2,column=4)

        self.button8=ttk.Button(self.btmframe,image=hme_btn,text='Home',tooltip='Go Home (your drunk)',command=lambda: controller.show_frame(HomePage),compound="top")
        self.button8.image=hme_btn 
        self.button8.grid(row=1,column=1,padx=5,pady=10)

        self.button9=ttk.Button(self.btmframe,image=info_btn,text='Help',command=self.popup_window,tooltip='Press for more help',compound="top")
        self.button9.image=info_btn  
        self.button9.grid(row=1,column=2,padx=5,pady=10)

        self.button10=ttk.Button(self.btmframe,text='Quit',image=ext_btn,tooltip='Quit software and all running processes',command=controller.enditall,compound="top")
        self.button10.image=ext_btn 
        self.button10.grid(row=1,column=3,padx=5,pady=10)

        self.button11=ttk.Button(self.btmframe,text='Back',image=bck_btn,command=lambda: controller.show_frame(ImageCalibrator),compound="top")
        self.button11.image=bck_btn
        self.button11.grid(row=0,column=2,pady=5)

        #---ENTRIES---#
        self.entry1=ttk.Entry(self.midframe,textvariable=self.rawfolder,width=75)
        self.entry1.grid(row=1,column=2,padx=5,columnspan=2)
        self.entry2=ttk.Entry(self.midframe,textvariable=self.t5file,width=75)
        self.entry2.grid(row=2,column=2,padx=5,columnspan=2)
        self.entry3=ttk.Entry(self.midframe,textvariable=self.vigfolder,width=75)
        self.entry3.grid(row=3,column=2,padx=5,columnspan=2)
        self.entry4=ttk.Entry(self.midframe,textvariable=self.outfolder,width=75)
        self.entry4.grid(row=4,column=2,padx=5,columnspan=2)
        self.batchbox=tk.Text(self.midframe,width=50,height=10)
        self.batchbox.grid(row=8,column=2,columnspan=2, padx=10, pady=5)

## Shapefile Class: defines the variables for the appearance and function of the shapefile generator Tool.
class Shapefilegenerator(ttk.Frame):
    def popup_window(self):
        win_x = self.winfo_rootx()+300
        win_y = self.winfo_rooty()+100
        window = tk.Toplevel()
        window.geometry(f'+{win_x}+{win_y}')
        window.title('Shapefile Generator - Help')

        label = tk.Label(window, text='''
        Shapefile = the input shapefile generated using GIS software identifying plot names and locations.
        
        Output file = the output file location ane name of the generated geoJSON file.
                         ''',justify='left')
        label.pack(fill='x', padx=50, pady=50)

        button_close = ttk.Button(window, text="Close", command=window.destroy)
        button_close.pack(fill='x')
    def get_shapefile(self):
        folder=tk.filedialog.askopenfilename(initialdir = "/",title = 'Shapefile',filetypes=(("shp","*.shp"),("all files","*.*")))
        self.shapefile.set(folder)
        
    def get_outfilename(self):
        folder=tk.filedialog.asksaveasfilename(initialdir = os.path.abspath(os.path.join(self.shapefile.get(),'../')),title = 'Output file',filetypes=(("geojson","*.geojson"),("all files","*.*")))
        self.out_file.set(folder)
        self._toggle_state('normal')
        
    def run(self):
        if self.out_file.get() == 'blank':
            tk.messagebox.showinfo("Select Output file", "Please define a file name and location")
        else:    
            self._toggle_state('disabled')
            try:
                shapefile_gen(self.shapefile.get(),self.out_file.get())
                tk.messagebox.showinfo("Processing Complete", "Processing Complete")
                self._toggle_state('normal')
            except Exception as e:
                tk.messagebox.showerror("Error", e)
                traceback.print_exc()
                self._toggle_state('normal')

    def _toggle_state(self, state):
        state = state if state in ('normal', 'disabled') else 'normal'
        widgets = (self.button1, self.button2,self.button3)
        for widget in widgets:
            widget.configure(state=state)
    def __init__(self,parent,controller):
        tk.Frame.__init__(self,parent)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.topframe = tk.Frame(self)
        self.midframe = tk.Frame(self)
        self.btmframe = tk.Frame(self)
        
        self.topframe.grid(row=0)
        self.midframe.grid(row=1)
        self.btmframe.grid(row=2)

         #---VARIABLES---#
        self.shapefile=tk.StringVar()
        self.shapefile.set('blank')
        self.out_file=tk.StringVar()
        self.out_file.set('blank')
        info_btn = PhotoImage(file=info_button,master=self).subsample(5,5)
        hme_btn = PhotoImage(file=home_button,master=self).subsample(5,5)
        ext_btn = PhotoImage(file=exit_button,master=self).subsample(5,5)

        self.label=tk.Label(self.topframe,text='Shapefile to GeoJSON',font=Large_Font)
        self.label.grid(row=0,column=2,padx=10)
        
        self.label=tk.Label(self.topframe,text='Convert plot shapefiles (.shp) to GeoJSON for storage and further processing.',font=Norm_Font)
        self.label.grid(row=1,column=2,padx=10)

        self.button1=ttk.Button(self.midframe,text='Shapefile (.shp)',command=self.get_shapefile,width=20)
        self.button1.grid(row=2,column=1,pady=10)
        self.button2=ttk.Button(self.midframe,text='Output file (.geojson)',command=self.get_outfilename,width=20)
        self.button2.grid(row=3,column=1,pady=10)
        self.button3=ttk.Button(self.midframe,text='Run',command=self.run,width=15)
        self.button3.configure(state='disabled')
        self.button3.grid(row=10,column=2,pady=10)

        self.button8=ttk.Button(self.btmframe,image=hme_btn,text='Home',tooltip='Go Home (your drunk)',command=lambda: controller.show_frame(HomePage),compound="top")
        self.button8.image=hme_btn 
        self.button8.grid(row=1,column=1,padx=5,pady=10)

        self.button9=ttk.Button(self.btmframe,image=info_btn,text='Help',command=self.popup_window,tooltip='Press for more help',compound="top")
        self.button9.image=info_btn  
        self.button9.grid(row=1,column=2,padx=5,pady=10)

        self.button10=ttk.Button(self.btmframe,text='Quit',image=ext_btn,tooltip='Quit software and all running processes',command=controller.enditall,compound="top")
        self.button10.image=ext_btn 
        self.button10.grid(row=1,column=3,padx=5,pady=10)

          #---ENTRIES---#
        self.entry1=ttk.Entry(self.midframe,textvariable=self.shapefile,width=75)
        self.entry1.grid(row=2,column=2,padx=5)
        self.entry2=ttk.Entry(self.midframe,textvariable=self.out_file,width=75)
        self.entry2.grid(row=3,column=2,padx=5)
        
## HyperSpecExtractor Class: defines the variables for the appearance and function of the Hyperspec data extractor Tool.
class HyperSpecExtractor(ttk.Frame):
    def popup_window(self):
        win_x = self.winfo_rootx()+500
        win_y = self.winfo_rooty()+150
        window = tk.Toplevel()
        window.geometry(f'+{win_x}+{win_y}')
        window.title('UAV Data Extractor - Help')

        label = ImageLabel(window)
        label.pack(padx=10,pady=10)
        label.load(resource_path('Graphics\\'+str(randint(1,5))+'.gif'))

        button_close = ttk.Button(window, text="Close", command=window.destroy)
        button_close.pack(fill='x')
        
    def get_data(self):
        files=tk.filedialog.askopenfilenames(initialdir = "/",title = 'Source File')
        self.data.set([a for a in files]) 
        self.data_short.set([os.path.basename(b)+' ' for b in files])
        if os.path.isfile(files[0]):
            self.button5=ttk.Button(self.midframe,text='Results Output file (.csv)',command=lambda: self.get_outfilename(),tooltip='Output CSV path.',width=20)
            self.button5.grid(row=4,column=1,pady=10)
            self.entry4=ttk.Entry(self.midframe,textvariable=self.out_file,width=75)
            self.entry4.grid(row=4,column=2,columnspan=2,padx=5)
            self.get_outfilename()
        return(self.button5)
      
    # def get_swir(self):
    #     files=tk.filedialog.askopenfilenames(initialdir = "/",title = 'SWIR')
    #     self.swir.set(files)
    #     self.swir_short.set([os.path.basename(b)+' ' for b in files])
    #     if os.path.isfile(files[0]):
    #         self.button6=ttk.Button(self.midframe,text='SWIR Output file (.csv)',command=lambda: self.get_outfilename('swir'),tooltip='Output CSV path.',width=20)
    #         self.button6.grid(row=6,column=1,pady=10)
    #         self.entry5=ttk.Entry(self.midframe,textvariable=self.out_swir,width=75)
    #         self.entry5.grid(row=6,column=2,columnspan=2,padx=5) 
    #         self.get_outfilename('swir')
    #     return(self.button6)
        
    def get_shapefile(self):
        folder=tk.filedialog.askopenfilename(initialdir = "/",title = 'Shapefile',filetypes=(("geojson","*.geojson"),("all files","*.*")))
        self.shapefile.set(folder)

    def checkall(self):
        all = [self.checkMean,self.checkMedian,self.checkStdev,self.checkCount,self.checkPrcnt99,self.checkPrcnt90]
        if self.checkAll.instate(['selected']) == True:
            for a in all:
                if a.instate(['selected']) == False:
                    a.invoke()
        elif self.checkAll.instate(['selected']) == False:
                for a in all:
                    if a.instate(['selected']) == True:
                        a.invoke()
                    
    def get_outfilename(self):
        folder=tk.filedialog.asksaveasfilename(initialdir = os.path.abspath(os.path.join(self.shapefile.get(),'../')),title = 'Output file',filetypes=(("csv","*.csv"),("all files","*.*")))
        if '.csv'  not in folder:
            folder += '.csv'
        self.out_file.set(folder)    
        # if sensor.lower() == 'swir':
        #     self.out_swir.set(folder)
        # elif sensor.lower() == 'vnir':
        #     self.out_vnir.set(folder)
        self._toggle_state('normal')
    
    def monitor(self, thread):
        if thread.is_alive():
            # check the thread every 100ms
            self.after(100, lambda: self.monitor(thread))
        else:
            tk.messagebox.showinfo("Processing Complete", "Processing Complete")
            gc.collect()
            self._toggle_state('enabled')
        
    def run(self):
        if self.out_file.get() == '' and self.out_swir.get() == '':
            tk.messagebox.showinfo("Select Output file", "Please define an output file name and location")
        else:
            all = [self.checkMean,self.checkMedian,self.checkStdev,self.checkCount,self.checkPrcnt99,self.checkPrcnt90]
            samples = []
            for a in all:
                if a.instate(['selected']) == True:
                    samples.append(a.cget('text'))  
            self._toggle_state('disabled')
            if self.checkPrcntC.instate(['selected']) == True:
                if self.customPrcnt.get() == '':
                    tk.messagebox.showerror("Error", "Invalid percentile value")
                    self._toggle_state('normal')
                    return
                else:
                    samples.append({'custom':self.customPrcnt.get()})
                
            try:
                variables = {'outfile':self.out_file.get(),'shapefile':self.shapefile.get(),'samples':samples}
                layers = {'inFiles':self.data.get()}
                gc.collect()
                print(variables)
                print(layers)
                thread_1 = threading.Thread(target=hyperspec_master, args=(variables,layers))
                thread_1.setDaemon(True)
                thread_1.start()
                
                self.monitor(thread_1)
                
            except Exception as e:
                tk.messagebox.showerror("Error", e)
                traceback.print_exc()
                self._toggle_state('normal')

    def _toggle_state(self, state):
        state = state if state in ('normal', 'disabled') else 'normal'
        try:
            widgets = (self.button1, self.button2, self.button4, self.button5, self.button8,self.button9,self.button10)
        except:
            widgets = (self.button1, self.button2, self.button4, self.button5, self.button8,self.button9,self.button10)
        for widget in widgets:
            widget.configure(state=state)
    def __init__(self,parent,controller):
        tk.Frame.__init__(self,parent)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.topframe = tk.Frame(self)
        self.midframe = tk.Frame(self)
        self.btmframe = tk.Frame(self)
        
        self.topframe.grid(row=0)
        self.midframe.grid(row=1)
        self.btmframe.grid(row=2)

         #---VARIABLES---#
        self.data=tk.StringVar()
        self.data.set('')
        self.data_short=tk.StringVar()
        self.data_short.set('')        
        # self.swir=tk.StringVar()
        # self.swir.set('')
        # self.swir_short=tk.StringVar()
        # self.swir_short.set('')          
        self.shapefile=tk.StringVar()
        self.shapefile.set('')
        self.out_file=tk.StringVar()
        self.out_file.set('')
        # self.out_swir=tk.StringVar()
        # self.out_swir.set('')
        self.xmean = tk.IntVar()
        self.xmedian = tk.IntVar()
        self.xstdev = tk.IntVar()
        self.xcount = tk.IntVar()
        self.xprcnt99 = tk.IntVar()
        self.xprcnt90 = tk.IntVar()
        self.xprcntcstm = tk.IntVar()
        self.xall = tk.IntVar()
        info_btn = PhotoImage(file=info_button,master=self).subsample(5,5)
        hme_btn = PhotoImage(file=home_button,master=self).subsample(5,5)
        ext_btn = PhotoImage(file=exit_button,master=self).subsample(5,5)

        self.label=tk.Label(self.topframe,text='UAV Data Extractor',font=Large_Font)
        self.label.grid(row=0,column=2,padx=10)
        
        self.label=tk.Label(self.topframe,text='Extract and statistically sample areas of interest from spatial data.\n \n Hover over inputs/outputs for more info.',font=Norm_Font)
        self.label.grid(row=1,column=2,padx=10)

        self.button1=ttk.Button(self.midframe,text='Shapefile (.geojson)',command=self.get_shapefile,tooltip='GeoJSON file containing Area of Interest Polygons',width=20)
        self.button1.grid(row=2,column=1,pady=10)
        self.button2=ttk.Button(self.midframe,text='Input File',command=self.get_data,tooltip='Source file from which data will be extracted',width=20)
        self.button2.grid(row=3,column=1,pady=10)
        # self.button3=ttk.Button(self.midframe,text='SWIR',command=self.get_swir,tooltip='SWIR binary file from sensor (not .hdr!)',width=20)
        # self.button3.grid(row=5,column=1,pady=10)
        self.button4=ttk.Button(self.midframe,text='Run',command=self.run,width=15)
        self.button4.configure(state='disabled')
        self.button4.grid(row=11,column=2,pady=10,padx=75)

        self.checkframe=tk.Frame(self.midframe)
        self.checkframe.grid(row=10,column=2)
        self.checkMean=ttk.Checkbutton(self.checkframe,text='Mean',variable=self.xmean,onvalue='Mean')
        self.checkMean.grid(row=1,column=1)
        self.checkMedian=ttk.Checkbutton(self.checkframe,text='Median',variable=self.xmedian,onvalue='Median')
        self.checkMedian.grid(row=1,column=3)
        self.checkStdev=ttk.Checkbutton(self.checkframe,text='StDev',variable=self.xstdev,onvalue='StDev')
        self.checkStdev.grid(row=1,column=2)
        self.checkCount=ttk.Checkbutton(self.checkframe,text='Count',variable=self.xcount,onvalue='Count')
        self.checkCount.grid(row=2,column=1)
        self.checkPrcnt99=ttk.Checkbutton(self.checkframe,text='99th%',variable=self.xprcnt99,onvalue='99th%')
        self.checkPrcnt99.grid(row=2,column=2)
        self.checkPrcnt90=ttk.Checkbutton(self.checkframe,text='90th%',variable=self.xprcnt90,onvalue='90th%')
        self.checkPrcnt90.grid(row=2,column=3)
        self.checkAll=ttk.Checkbutton(self.checkframe,text='All',command=self.checkall,variable=self.xall)
        self.checkAll.grid(row=3,column=2)
        self.checkPrcntC=ttk.Checkbutton(self.checkframe,text='Custom Percentile (0-100)',variable=self.xprcntcstm,onvalue='Cstm%')
        self.checkPrcntC.grid(row=4,column=2)
        self.customPrcnt=ttk.Combobox(self.checkframe,width=5,values=natsorted([str(a) for a in range(0,101)]))
        self.customPrcnt.grid(row=4,column=3)

        self.button8=ttk.Button(self.btmframe,image=hme_btn,text='Home',tooltip='Go Home (your drunk)',command=lambda: controller.show_frame(HomePage),compound="top")
        self.button8.image=hme_btn 
        self.button8.grid(row=1,column=1,padx=5,pady=10)
        self.button9=ttk.Button(self.btmframe,image=info_btn,text='Help',command=self.popup_window,tooltip='Press for more help',compound="top")
        self.button9.image=info_btn  
        self.button9.grid(row=1,column=2,padx=5,pady=10)
        self.button10=ttk.Button(self.btmframe,text='Quit',image=ext_btn,tooltip='Quit software and all running processes',command=controller.enditall,compound="top")
        self.button10.image=ext_btn 
        self.button10.grid(row=1,column=3,padx=5,pady=10)

          #---ENTRIES---#
        self.entry1=ttk.Entry(self.midframe,textvariable=self.shapefile,width=75)
        self.entry1.grid(row=2,column=2,columnspan=2,padx=5)
        self.entry2=ttk.Entry(self.midframe,textvariable=self.data_short,width=75)
        self.entry2.grid(row=3,column=2,columnspan=2,padx=5)
        # self.entry3=ttk.Entry(self.midframe,textvariable=self.swir_short,width=75)
        # self.entry3.grid(row=5,column=2,columnspan=2,padx=5)

class OrthoMerging(ttk.Frame):
    def popup_window(self):
        win_x = self.winfo_rootx()+500
        win_y = self.winfo_rooty()+150
        window = tk.Toplevel()
        window.geometry(f'+{win_x}+{win_y}')
        window.title('HyperSpec Extractor - Help')

        label = tk.Label(window, text='''
        Inputs = orthomosaics for same field to be combined into one single multi-layer ortho.

        Output will be compressed using LZW and predictor 2, please ensure enough space on disk for temporary files.

        DEM (Digital Elevation Model) is the bare ground one, double check if you need to, but definitely bare ground.''',justify='left')
        label.pack(fill='x', padx=50, pady=50)

        button_close = ttk.Button(window, text="Close", command=window.destroy)
        button_close.pack(fill='x')
        
    def get_rgb(self):
        files=tk.filedialog.askopenfilename(initialdir = "/",title = 'RGB',filetype=(("tif","*.tif"),("all files","*.*")))
        self.rgb.set([a for a in files]) 
        self.rgb_short.set([os.path.basename(b)+' ' for b in files])
        # return(self.button5)
      
    def get_nir(self):
        files=tk.filedialog.askopenfilename(initialdir = "/",title = 'NIR',filetypes=(("tif","*.tif"),("all files","*.*")))
        self.nir.set(files)
        self.nir_short.set([os.path.basename(b)+' ' for b in files])
    
    def get_DEM(self):
        files=tk.filedialog.askopenfilename(initialdir = "/",title = 'Bare Ground DEM',filetypes=(("tif","*.tif"),("all files","*.*")))
        self.DEM.set(files)
        self.DEM_short.set([os.path.basename(b)+' ' for b in files])

    def get_DSM(self):
        files=tk.filedialog.askopenfilename(initialdir = "/",title = 'DSM',filetypes=(("tif","*.tif"),("all files","*.*")))
        self.DSM.set(files)
        self.DSM_short.set([os.path.basename(b)+' ' for b in files])

    def get_Other(self):
        files=tk.filedialog.askopenfilename(initialdir = "/",title = 'Other File',filetypes=(("tif","*.tif"),("all files","*.*")))
        other_name=tk.simpledialog.askstring(title='Layer Name',prompt='Provide a name for this layer (e.g. Thermal)')
        self.other_file.set(files)
        self.other.set(other_name)
                    
    def get_outfilename(self):
        folder=tk.filedialog.asksaveasfilename(initialdir = os.path.abspath(os.path.join(self.rgb.get(),'../')),title = 'Output file',filetypes=(("tif","*.tif"),("all files","*.*")))
        if '.tif'  not in folder:
            folder += '.tif'
        self.out_file.set(folder)
        self._toggle_state('normal')
    
    def monitor(self, thread):
        if thread.is_alive():
            # check the thread every 100ms
            self.after(100, lambda: self.monitor(thread))
        else:
            tk.messagebox.showinfo("Processing Complete", "Processing Complete")
            gc.collect()
            self._toggle_state('enabled')
        
    def run(self):
        if self.out_file.get() == '':
            tk.messagebox.showinfo("Select Output file", "Please define a file name and location")
        else:
            self._toggle_state('disabled')
            try:
                others = (self.other.get(),self.other_file.get())
                gc.collect()
                thread_1 = threading.Thread(target=orthoMerge, args=(self.rgb.get(),self.nir.get(),self.DEM.get(),self.DSM.get(),others,self.out_file.get()))
                thread_1.setDaemon(True)
                thread_1.start()
                
                self.monitor(thread_1)
                
            except Exception as e:
                tk.messagebox.showerror("Error", e)
                traceback.print_exc()
                self._toggle_state('normal')

    def _toggle_state(self, state):
        state = state if state in ('normal', 'disabled') else 'normal'
        try:
            widgets = (self.button1, self.button2, self.button3, self.button4, self.button5, self.button6, self.button7)
        except:
            widgets = (self.button1, self.button2, self.button3, self.button4, self.button5, self.button8,self.button9,self.button10)
        for widget in widgets:
            widget.configure(state=state)
    def __init__(self,parent,controller):
        tk.Frame.__init__(self,parent)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.topframe = tk.Frame(self)
        self.midframe = tk.Frame(self)
        self.btmframe = tk.Frame(self)
        
        self.topframe.grid(row=0)
        self.midframe.grid(row=1)
        self.btmframe.grid(row=2)

         #---VARIABLES---#
        self.rgb=tk.StringVar()
        self.rgb.set('')
        self.rgb_short=tk.StringVar()
        self.rgb_short.set('')        
        self.nir=tk.StringVar()
        self.nir.set('')
        self.nir_short=tk.StringVar()
        self.nir_short.set('')          
        self.DEM=tk.StringVar()
        self.DEM.set('')
        self.DEM_short=tk.StringVar()
        self.DEM_short.set('')
        self.DSM=tk.StringVar()
        self.DSM.set('')
        self.DSM_short=tk.StringVar()
        self.DSM_short.set('')
        self.other=tk.StringVar()
        self.other.set('')
        self.other_file=tk.StringVar()
        self.other_file.set('')
        self.out_file=tk.StringVar()
        self.out_file.set('')

        info_btn = PhotoImage(file=info_button,master=self).subsample(5,5)
        hme_btn = PhotoImage(file=home_button,master=self).subsample(5,5)
        ext_btn = PhotoImage(file=exit_button,master=self).subsample(5,5)

        self.label=tk.Label(self.topframe,text='Orthophoto Merger',font=Large_Font)
        self.label.grid(row=0,column=2,padx=10)
        
        self.label=tk.Label(self.topframe,text='Merge orthophotos into a single multilayer orthophoto, compressed using LZW(2).\n \n Hover over inputs/outputs for more info.\n \n DEM = Bare Ground; DSM = the one with crops in.',font=Norm_Font)
        self.label.grid(row=1,column=2,padx=10)

        self.button1=ttk.Button(self.midframe,text='RGB',command=self.get_rgb,tooltip='RGB orthomosaic',width=20)
        self.button1.grid(row=2,column=1,pady=10)
        self.button2=ttk.Button(self.midframe,text='NIR',command=self.get_nir,tooltip='NIR orthomosaic',width=20)
        self.button2.grid(row=3,column=1,pady=10)
        self.button3=ttk.Button(self.midframe,text='DEM (BG)',command=self.get_nir,tooltip='Bare Ground DEM',width=20)
        self.button3.grid(row=4,column=1,pady=10)
        self.button4=ttk.Button(self.midframe,text='DSM',command=self.get_nir,tooltip='Digital Surface Model (with crops!)',width=20)
        self.button4.grid(row=5,column=1,pady=10)
        self.button5=ttk.Button(self.midframe,text='Other',command=self.get_Other,tooltip='Any other orthomosaic to include (e.g. Thermal)',width=20)
        self.button5.grid(row=6,column=1,pady=10)
        self.button6=ttk.Button(self.midframe,text='OutFile',command=self.get_outfilename,tooltip='Outpath for generated orthomosaic (.tif)',width=20)
        self.button6.grid(row=7,column=1,pady=10)
        self.button7=ttk.Button(self.midframe,text='Run',command=self.run,width=15)
        self.button7.configure(state='disabled')
        self.button7.grid(row=11,column=2,pady=10,padx=75)

        self.button8=ttk.Button(self.btmframe,image=hme_btn,text='Home',tooltip='Go Home (your drunk)',command=lambda: controller.show_frame(HomePage),compound="top")
        self.button8.image=hme_btn 
        self.button8.grid(row=1,column=1,padx=5,pady=10)
        self.button9=ttk.Button(self.btmframe,image=info_btn,text='Help',command=self.popup_window,tooltip='Press for more help',compound="top")
        self.button9.image=info_btn  
        self.button9.grid(row=1,column=2,padx=5,pady=10)
        self.button10=ttk.Button(self.btmframe,text='Quit',image=ext_btn,tooltip='Quit software and all running processes',command=controller.enditall,compound="top")
        self.button10.image=ext_btn 
        self.button10.grid(row=1,column=3,padx=5,pady=10)

          #---ENTRIES---#
        self.entry1=ttk.Entry(self.midframe,textvariable=self.rgb_short,width=75)
        self.entry1.grid(row=2,column=2,columnspan=2,padx=5)
        self.entry2=ttk.Entry(self.midframe,textvariable=self.nir_short,width=75)
        self.entry2.grid(row=3,column=2,columnspan=2,padx=5)
        self.entry3=ttk.Entry(self.midframe,textvariable=self.DEM,width=75)
        self.entry3.grid(row=4,column=2,columnspan=2,padx=5)
        self.entry4=ttk.Entry(self.midframe,textvariable=self.DSM,width=75)
        self.entry4.grid(row=5,column=2,columnspan=2,padx=5)
        self.entry5=ttk.Entry(self.midframe,textvariable=self.other_file,width=75)
        self.entry5.grid(row=6,column=2,columnspan=2,padx=5)
        self.entry6=ttk.Entry(self.midframe,textvariable=self.out_file,width=75)
        self.entry6.grid(row=7,column=2,columnspan=2,padx=5)

if __name__ == "__main__":
    app=software()
    app.geometry("1200x900")
    app.mainloop()