# -*- coding: utf-8 -*-

"""
author: George Routis

Added (by George Routis): 
    1) Calculate vegetation indices (VI) menu  and submenus and the related image processing code for each VI.
    2) Information menu and submenus and the related code where the user can get informed by the VI related equation.
    3) "Open RGB Image File" button and "Open Reflectance Image File" button where the user can choose either RGB UAV image or Reflectance UAV image or both images in order to use it further in the APP. 
    4) Button for cleaning "IMAGES" folder.
    5) Implement single linear regression models on Excel and coefficient extractions that are used inside the following code.
    6) Information windows to the user
    
    credits:
        - https://github.com/Axel-Erfurt/OrthoViewLite/blob/main/OrthoViewLite.py by Axel Schneider
"""
# ------------------ OPENCV ------------------------------
#from __future__ import print_function
#from __future__ import division
#import cv2 as cv
#import numpy as np
#import argparse
# --------------------------------------------------------

import os
import sys
import cv2
from matplotlib.figure import Figure
import numpy as np
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QMainWindow, QApplication, QWidget,QAction, QFileDialog, QMenu, 
                             QToolBar, QHBoxLayout, QTreeView, QFileSystemModel, QSizePolicy, 
                             QMessageBox)
from PyQt5.QtCore import Qt, QDir, QStandardPaths, QFileInfo
import matplotlib.backends.backend_qt5agg as mpl_qt
import tifffile as tiff

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from osgeo import gdal
from osgeo.gdalconst import *

try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser


selfDir = os.path.dirname(__file__)
iniApp = (os.path.join(selfDir, 'OrthoViewList.ini'))
config = ConfigParser(
    dict(pos='[0, 0]', corners='[None]*4', scalex=0, scaley=0))
config.add_section('window')
config.read(iniApp)

INITIAL_UAV_RGB_IMAGE_PATH = "empty"
INITIAL_UAV_REF_IMAGE_PATH = "empty"

REAL_TIME_INFORMATION_STRING = ""

def write_config():
    with open(iniApp, 'w+') as cf:
        config.write(cf)


class MyToolBar(mpl_qt.NavigationToolbar2QT): 
    from osgeo import ogr, gdal, osr
    import numpy as np

    def __init__(self, canvas, ortho):
        super().__init__(canvas, ortho)
        self.ortho = ortho
    
    def set_message(self, s):
        try:
            sstr = s.split()

            while len(sstr) > 5:
                del sstr[0]
            x, y = float(sstr[0][2:]), float(sstr[1][2:])
            s = f'x = {x:.2f}\ny = {y:.2f}'
        except Exception:
            pass

        if self.coordinates:
            self.locLabel.setText(s)

from PyQt5 import QtWidgets, QtCore
class MyMplCanvas(mpl_qt.FigureCanvasQTAgg): 
    def __init__(self, parent=None):
        self.fig = Figure()
        self.fig.patch.set_facecolor('None')
        super(MyMplCanvas, self).__init__(self.fig)
        self.setParent(parent)
        self.updateGeometry()
        self.setupPlot()
        self.mpl_connect('button_press_event', self.onPress)
        self.img = None
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.mouseClickPos = None
        self.menu = QMenu()

    def setupPlot(self):
        rect = [0., 0., 1., 1.]
        self.axes = self.fig.add_axes(rect)
        self.axes.axis("off")

    def imshow(self, img):
        if self.img is None:
            self.img = self.axes.imshow(img)
        else:
            prev = self.img.get_array()
            self.img.set_data(img)
            if prev.shape != img.shape:
                self.img.set_extent(
                    [-0.5, img.shape[1]-0.5, img.shape[0]-0.5, -0.5])
                self.axes.set_xlim((0, img.shape[1]))
                self.axes.set_ylim((img.shape[0], 0))
                self.toolbar.update()
        self.draw()
    def onPress(self, event):
        if (event.xdata is None) or (event.ydata is None):
            self.mouseClickPos = None
            return
        self.mouseClickPos = int(round(event.xdata)), int(round(event.ydata))
                        
class Show_Real_Time_Information(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Information...")
        self.layout = QVBoxLayout()
        self.textEdit = QTextEdit()
        global REAL_TIME_INFORMATION_STRING
        self.textEdit.setPlainText(str(REAL_TIME_INFORMATION_STRING))
        self.layout.addWidget(self.textEdit)
        self.textEdit.setReadOnly(True)
        self.setLayout(self.layout)

class OrthoView(QMainWindow):
    def __init__(self, parent=None):
        super(OrthoView, self).__init__(parent)
        self.UAV_RGB_image_path = "empty" 
        self.UAV_REFLECTANCE_image_path = "empty" 
        self.splitted_word_before_full_stop = ""
        self.CURRENT_LEAF_AREA_INDEX_IMAGE = "empty"
        
        print("READING MyToolBar_flag_RGB...")
        self.MyToolBar_flag_RGB = 0
        
        print("READING MyToolBar_flag_REF...")
        self.MyToolBar_flag_REF = 0
        
        self.setWindowTitle('OrthoViewLite')
        self.setStyleSheet("QMainWindow {background: #e9e9e9;} QHBoxLayout \
                            {background: #e9e9e9;} QTreeView {background: #e9e9e9;}  \
                            FigureCanvasQTAgg {background: #e9e9e9;} QToolBar {border: 0px;}")
        self.setMinimumSize(500, 350)
        self.image_file_path = ""   
        if config.has_option('window', 'win_left') and config.has_option('window', 'win_top') \
            and config.has_option('window', 'win_width') and config.has_option('window', 'win_height'):
            left = int(config.get('window', 'win_left'))
            top = int(config.get('window', 'win_top'))
            width = int(config.get('window', 'win_width'))
            height = int(config.get('window', 'win_height'))
            self.setGeometry (left, top, width, height)
            
        self.home_path = QStandardPaths.standardLocations(QStandardPaths.PicturesLocation)[0]

        self.tb = QToolBar("File")
        
        empty = QWidget()
        empty.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tb.addWidget(empty)
        
        open_button_RGB = QAction("Open RGB Image File", self, triggered=self.open_RGB_Image_File)  
        open_button_RGB.setIcon(QIcon.fromTheme("document-open"))
        self.tb.addAction(open_button_RGB)
        
        open_button_REF = QAction("Open Reflectance Image File", self, triggered=self.open_Reflectance_Image_File)  
        open_button_REF.setIcon(QIcon.fromTheme("document-open")) 
        self.tb.addAction(open_button_REF) 
        
        from PyQt5 import QtWidgets
        from PyQt5.QtGui import QPixmap

        stretch = QWidget()
        stretch.setFixedWidth(200)
        self.tb.addWidget(stretch)

        self.plotCanvas = MyMplCanvas(self)
        self.plotCanvas.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar = MyToolBar(self.plotCanvas, self)
                
        for action in self.toolbar.findChildren(QAction):
            if action.text() in ['Customize', 'Subplots']:
                action.setVisible(False)
        self.toolbar.locLabel.setAlignment(Qt.AlignRight)
        self.toolbar.locLabel.setFixedWidth(200)

        self.tb.setContextMenuPolicy(Qt.PreventContextMenu)
        self.tb.setMovable(False)
        self.tb.setAllowedAreas(Qt.TopToolBarArea)
        self.toolbar.setContextMenuPolicy(Qt.PreventContextMenu)
        self.toolbar.setMovable(False)
        self.toolbar.setAllowedAreas(Qt.TopToolBarArea)
        self.addToolBar(self.toolbar)
        self.addToolBar(self.tb)

        mylayout = QHBoxLayout()
        mylayout.addWidget(self.plotCanvas)
        
        self.fileModel = QFileSystemModel()
        self.fileModel.setFilter(QDir.NoDotAndDotDot | QDir.Files | QDir.AllDirs)
        self.fileModel.setRootPath(QDir.homePath())
 
        mywidget = QWidget()
        mywidget.setLayout(mylayout)
        self.setCentralWidget(mywidget)
        
        self.myfilter = ["tif", "tiff", "png", "jpg"]
        self.treefilter = ["*.tif", "*.tiff", "*.png", "*.jpg"]
        
        self.fileModel.setNameFilters(self.treefilter)
        self.fileModel.setNameFilterDisables(False)
        
        bar=self.menuBar()  
        file=bar.addMenu("Calculate") 
        
        calc_S6 = QAction("Salinity S6 (Reflectance)", self) 
        file.addAction(calc_S6)
        calc_S6.triggered.connect(self.calculate_Salinity_S6) 
        
        calc_SI = QAction("Salinity SI (RGB)", self) 
        file.addAction(calc_SI) 
        calc_SI.triggered.connect(self.calculate_Salinity_SI) 
        
        calc_SI4 = QAction("Salinity SI4 (RGB)", self) 
        file.addAction(calc_SI4)
        calc_SI4.triggered.connect(self.calculate_Salinity_SI4) 
        
        calc_Int1 = QAction("Intensity index Int1 (RGB)", self) 
        file.addAction(calc_Int1) 
        calc_Int1.triggered.connect(self.calculate_Intensity_index_Int1) 
        
        calc_Int2 = QAction("Intensity index Int2 (Reflectance)", self) 
        file.addAction(calc_Int2) 
        calc_Int2.triggered.connect(self.calculate_Intensity_index_Int2) 
        
        calc_NDVI = QAction("NDVI (Reflectance)", self) 
        file.addAction(calc_NDVI) 
        calc_NDVI.triggered.connect(self.calculate_NDVI)
        
        calc_SAVI = QAction("SAVI (Reflectance)", self) 
        file.addAction(calc_SAVI) 
        calc_SAVI.triggered.connect(self.calculate_SAVI) 
        
        calc_MSAVI2 = QAction("MSAVI2 (Reflectance)", self)
        file.addAction(calc_MSAVI2)
        calc_MSAVI2.triggered.connect(self.calculate_MSAVI2)
        
        calc_RENDVI = QAction("RENDVI (Reflectance)", self)
        file.addAction(calc_RENDVI)
        calc_RENDVI.triggered.connect(self.calculate_RENDVI)
        
        file = bar.addMenu("Information")      
        
        show_S6_equation = QAction("Show S6 equation", self) 
        file.addAction(show_S6_equation) 
        show_S6_equation.triggered.connect(self.S6_equation) 
        
        show_SI_equation = QAction("Show SI equation", self) 
        file.addAction(show_SI_equation) 
        show_SI_equation.triggered.connect(self.SI_equation) 
        
        show_SI4_equation = QAction("Show SI4 equation", self) 
        file.addAction(show_SI4_equation) 
        show_SI4_equation.triggered.connect(self.SI4_equation) 
        
        show_Int1_equation = QAction("Show Int1 equation", self) 
        file.addAction(show_Int1_equation) 
        show_Int1_equation.triggered.connect(self.Int1_equation) 
        
        show_Int2_equation = QAction("Show Int2 equation", self) 
        file.addAction(show_Int2_equation) 
        show_Int2_equation.triggered.connect(self.Int2_equation) 
        
        show_NDVI_equation = QAction("Show NDVI equation", self) 
        file.addAction(show_NDVI_equation) 
        show_NDVI_equation.triggered.connect(self.NDVI_equation) 
        
        show_SAVI_equation = QAction("Show SAVI equation", self) 
        file.addAction(show_SAVI_equation) # SAVI
        show_SAVI_equation.triggered.connect(self.SAVI_equation) 
        
        show_MSAVI2_equation = QAction("Show MSAVI2 equation", self) 
        file.addAction(show_MSAVI2_equation) 
        show_MSAVI2_equation.triggered.connect(self.MSAVI2_equation)
        
        show_RENDVI_equation = QAction("Show RENDVI equation", self) 
        file.addAction(show_RENDVI_equation) 
        show_RENDVI_equation.triggered.connect(self.RENDVI_equation)
 
        file = bar.addMenu("Control")  
        
        clean_data = QAction("Clean data folder", self)
        file.addAction(clean_data)
        clean_data.triggered.connect(self.clean_data_folder)
        
        self.setLayout(mylayout) 
        self.setWindowTitle("menu demo") 
        
    def processtrigger(self,q):  
        print(q.text()+" is triggered") 
            
    def goHome(self):
       self.mylistwidget.setRootIndex(self.fileModel.index(self.home_path)) 
       
    def oneUp(self):
       self.mylistwidget.setRootIndex(self.mylistwidget.rootIndex().parent()) 

    def on_clicked(self):
        path = self.fileModel.fileInfo(self.mylistwidget.currentIndex()).absoluteFilePath()
        if QDir.exists(QDir(path)):
            print(path, "is folder")
        else:
            if QFileInfo(path).suffix() in self.myfilter:
                if not os.stat(path).st_size == 0:
                    print(path)
                    self.image_file_path = path
                    self.updateFrame()
                else:
                    print("file not exists or has size 0")
                    self.msgbox("File is empty (size 0)") 
                    
    def open_RGB_Image_File(self): 
        print("open File Dialog")
        path, _ = QFileDialog.getOpenFileName(self, "Open File", self.image_file_path,"Image Files (*.tif *.tiff *.png *.jpg)")
        print("image_file_path (RGB) = ", self.image_file_path)
        self.UAV_RGB_image_path = path

        if(self.MyToolBar_flag_RGB == 0):
            global INITIAL_UAV_RGB_IMAGE_PATH
            INITIAL_UAV_RGB_IMAGE_PATH = path
            self.MyToolBar_flag_RGB = 1
         
        print("UAV_RGB_image_path", self.UAV_RGB_image_path)   
        
        # split starts from here...
        path_to_split = path
        import os
        path_to_split.split(os.sep) 
        vector = path_to_split.split(os.sep) 
        self.tif_label = vector[-1] 
        import re
        a = self.tif_label
        self.splitted_word_before_full_stop, splitted_word_after_full_stop = a.split('.', 1)

        print("RGB Image path: ",self.UAV_RGB_image_path)
        if path:
            if os.path.isfile(path) and not os.stat(path).st_size == 0:
                self.image_file_path = path
                print("file exists:",self.image_file_path)
                self.updateFrame()
            else:
                print("file not exists or has size 0")      
                self.msgbox("File is empty (size 0)")            

    def open_Reflectance_Image_File(self):
        print("open File Dialog")
        path, _ = QFileDialog.getOpenFileName(self, "Open File", self.image_file_path,"Image Files (*.tif *.tiff *.png *.jpg)") 
        print("image_file_path (REF) = ", self.image_file_path)
        self.UAV_REFLECTANCE_image_path = path
        
        if(self.MyToolBar_flag_REF == 0):
            global INITIAL_UAV_REF_IMAGE_PATH
            INITIAL_UAV_REF_IMAGE_PATH = path
            self.MyToolBar_flag_REF = 1
            
        print("UAV_REFLECTANCE_image_path", self.UAV_REFLECTANCE_image_path)
        path_to_split = path
        import os
        path_to_split.split(os.sep) 
        vector = path_to_split.split(os.sep) 
        self.tif_label = vector[-1] 
        import re
        a = self.tif_label
        self.splitted_word_before_full_stop_REF, splitted_word_after_full_stop_REF = a.split('.', 1)
        print("Reflectance Image path: ",path)
        if path:
            if os.path.isfile(path):
                self.image_file_path = path
                print("file exists:",self.image_file_path)
                isTest = True
                self.updateFrame()
            else:
                print("file not exists")     

    def getFrame(self, path):
        if os.path.isfile(path):
            dataset = gdal.Open(path)
            band = dataset.GetRasterBand(1)
            frame = cv2.imread(path, 1)
            IMAGE_HEIGHT = band.YSize
            IMAGE_WIDTH = band.XSize
            print("IMAGE_HEIGHT...", IMAGE_HEIGHT)
            print("IMAGE_WIDTH...", IMAGE_WIDTH)
            if not np.shape(frame) == ():
                self.img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                print("Error!")
                frame = cv2.imread(path, cv2.IMREAD_UNCHANGED)
                self.img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            self.openFile()

    def updateFrame(self):
        self.getFrame(self.image_file_path)
        overlay = self.img.copy()
        alpha = 0.75  # transparency factor
        imageNew = cv2.addWeighted(overlay, alpha, self.img, 1-alpha, 0)
        self.plotCanvas.imshow(imageNew)
        
    def closeEvent(self, e):
        config.set('window', 'win_left', str(self.geometry().x()))
        config.set('window', 'win_top', str(self.geometry().y()))
        config.set('window', 'win_width', str(self.geometry().width()))
        config.set('window', 'win_height', str(self.geometry().height()))
        
        with open(iniApp, 'w+') as cf:
            config.write(cf)

    def msgbox(self, message):
        msg = QMessageBox(2, "Error", message, QMessageBox.Ok)
        msg.exec()
    
    def calculate_Salinity_S6(self):
        print("Calculating Salinity S6...")
        import rasterio, os
        import cv2
        import numpy as np
        import pandas as pd
         
        with rasterio.open(self.UAV_REFLECTANCE_image_path) as f:
            profile = f.profile
            green = f.read(1)
            red = f.read(2)
            rededge = f.read(3)
            nir = f.read(4)
        result = (red * nir)/green
        tiff.imwrite('IMAGES/' + self.splitted_word_before_full_stop_REF + '_REFLECTANCE_S6.tif', result, photometric='rgb') 
        self.CURRENT_LEAF_AREA_INDEX_IMAGE = 'IMAGES/' + self.splitted_word_before_full_stop_REF + '_REFLECTANCE_S6.tif'
         
        # here I calculate the VI of the image....
        img = cv2.imread(self.CURRENT_LEAF_AREA_INDEX_IMAGE, cv2.IMREAD_UNCHANGED)
        rows,cols = img.shape
        sum = 0
        counter = 0 
        for i in range(0,rows):
            for j in range(0,cols):
                if(pd.isna(img[i,j])==False):
                    sum = sum + float(img[i,j])
                    counter = counter + 1
        VI = sum/counter
        print("VI = ", VI)
        # regression equation 
        # x is the VI of the whole image and y is the output, the calculated salinity
        y = (-3.1588) * VI + 1.4114
        SD = 0.157925246
        range_min = round((y - SD),4)
        range_max = round((y + SD),4)
        # result of the salinity... 
        print("S6 calculated...")
        # print("Salinity of the image = [ " + str(range_min) + " - " + str(range_max) + " ]") # enable this if you want to see the real salinity values (either positive or negative) 
         
        global REAL_TIME_INFORMATION_STRING  
        if( ((range_min > 0) or (range_min ==0)) and ((range_max > 0) or (range_max ==0)) ):
            REAL_TIME_INFORMATION_STRING = "S6 calculated. Salinity of the image = [ " + str(range_min) + " - " + str(range_max) + " ] dS/m"
            self.w = Show_Real_Time_Information()
            self.w.show()
        elif( (range_min < 0) and ((range_max > 0) or (range_max ==0)) ):
            REAL_TIME_INFORMATION_STRING = "S6 calculated. Salinity of the image = [ 0 - " + str(range_max) + " ] dS/m"
            self.w = Show_Real_Time_Information()
            self.w.show()
        if((range_min < 0) and (range_max < 0)):
            REAL_TIME_INFORMATION_STRING = "S6 calculated. Salinity cannot be calculated. Please use one of the other methods..."
            self.w = Show_Real_Time_Information()
            self.w.show()
    
    def calculate_Salinity_SI(self):
        print("Calculating Salinity SI...")
        import rasterio, os
        import cv2
        import numpy as np
        import pandas as pd
         
        with rasterio.open(self.UAV_RGB_image_path) as f:
            profile = f.profile
            blue = f.read(1)
            green = f.read(2)
            red = f.read(3)
        result = (blue * red)**0.5
        tiff.imwrite('IMAGES/' + self.splitted_word_before_full_stop + '_RGB_SI.tif', result, photometric='rgb') 
        self.CURRENT_LEAF_AREA_INDEX_IMAGE = 'IMAGES/' + self.splitted_word_before_full_stop + '_RGB_SI.tif'
         
        # here I calculate the VI of the image....
        img = cv2.imread(self.CURRENT_LEAF_AREA_INDEX_IMAGE, cv2.IMREAD_UNCHANGED)
        rows,cols = img.shape
        sum = 0
        counter = 0 
        for i in range(0,rows):
            for j in range(0,cols):
                if(pd.isna(img[i,j])==False):
                    sum = sum + float(img[i,j])
                    counter = counter + 1
        VI = sum/counter
        print("VI = ", VI)
        # regression equation 
        # x is the VI of the whole image and y is the output, the calculated salinity
        y = (-10.485) * VI + 1.167
        SD = 0.100947631
        range_min = round((y - SD),4)
        range_max = round((y + SD),4)
        # result of the salinity... 
        print("SI calculated...")
        #print("Salinity of the image = [ " + str(range_min) + " - " + str(range_max) + " ]") # enable this if you want to see the real salinity values (either positive or negative) 
         
        global REAL_TIME_INFORMATION_STRING  
        if( ((range_min > 0) or (range_min ==0)) and ((range_max > 0) or (range_max ==0)) ):
            REAL_TIME_INFORMATION_STRING = "SI calculated. Salinity of the image = [ " + str(range_min) + " - " + str(range_max) + " ] dS/m"
            self.w = Show_Real_Time_Information()
            self.w.show()
        elif( (range_min < 0) and ((range_max > 0) or (range_max ==0)) ):
            REAL_TIME_INFORMATION_STRING = "SI calculated. Salinity of the image = [ 0 - " + str(range_max) + " ] dS/m"
            self.w = Show_Real_Time_Information()
            self.w.show()
        if((range_min < 0) and (range_max < 0)):
            REAL_TIME_INFORMATION_STRING = "SI calculated. Salinity cannot be calculated. Please use one of the other methods..."
            self.w = Show_Real_Time_Information()
            self.w.show()
    
    def calculate_Salinity_SI4(self):
        print("Calculating Salinity SI4...")
        import rasterio, os
        import cv2
        import numpy as np
        import pandas as pd
         
        with rasterio.open(self.UAV_RGB_image_path) as f:
            profile = f.profile
            blue = f.read(1)
            green = f.read(2)
            red = f.read(3)
        result = ((green * green) + (red * red)) ** 0.5
        tiff.imwrite('IMAGES/' + self.splitted_word_before_full_stop +  '_RGB_SI4.tif', result, photometric='rgb') 
        self.CURRENT_LEAF_AREA_INDEX_IMAGE = 'IMAGES/' + self.splitted_word_before_full_stop +  '_RGB_SI4.tif'
         
        # here I calculate the VI of the image....
        img = cv2.imread(self.CURRENT_LEAF_AREA_INDEX_IMAGE, cv2.IMREAD_UNCHANGED)
        rows,cols = img.shape
        sum = 0
        counter = 0 
        for i in range(0,rows):
            for j in range(0,cols):
                if(pd.isna(img[i,j])==False):
                    sum = sum + float(img[i,j])
                    counter = counter + 1
        VI = sum/counter
        print("VI = ", VI)
        # regression equation 
        # x is the VI of the whole image and y is the output, the calculated salinity
        y = (-156.56) * VI + 0.8839
        SD = 0.112602834
        range_min = round((y - SD),4)
        range_max = round((y + SD),4)
        # result of the salinity... 
        print("SI4 calculated...")
        # print("Salinity of the image = [ " + str(range_min) + " - " + str(range_max) + " ]") # enable this if you want to see the real salinity values (either positive or negative) 
         
        global REAL_TIME_INFORMATION_STRING  
        if( ((range_min > 0) or (range_min ==0)) and ((range_max > 0) or (range_max ==0)) ):
            REAL_TIME_INFORMATION_STRING = "SI4 calculated. Salinity of the image = [ " + str(range_min) + " - " + str(range_max) + " ] dS/m"
            self.w = Show_Real_Time_Information()
            self.w.show()
        elif( (range_min < 0) and ((range_max > 0) or (range_max ==0)) ):
            REAL_TIME_INFORMATION_STRING = "SI4 calculated. Salinity of the image = [ 0 - " + str(range_max) + " ] dS/m"
            self.w = Show_Real_Time_Information()
            self.w.show()
        if((range_min < 0) and (range_max < 0)):
            REAL_TIME_INFORMATION_STRING = "SI4 calculated. Salinity cannot be calculated. Please use one of the other methods..."
            self.w = Show_Real_Time_Information()
            self.w.show()
    
    def calculate_Intensity_index_Int1(self):
        print("Calculating Index Int1...")
        import rasterio, os
        import cv2
        import numpy as np
        import pandas as pd
         
        with rasterio.open(self.UAV_RGB_image_path) as f:
            profile = f.profile
            blue = f.read(1)
            green = f.read(2)
            red = f.read(3)
        result = (green + red)/2
        tiff.imwrite('IMAGES/' + self.splitted_word_before_full_stop + '_RGB_Int1.tif', result, photometric='rgb') 
        self.CURRENT_LEAF_AREA_INDEX_IMAGE = 'IMAGES/' + self.splitted_word_before_full_stop + '_RGB_Int1.tif'
         
        # here I calculate the VI of the image....
        img = cv2.imread(self.CURRENT_LEAF_AREA_INDEX_IMAGE, cv2.IMREAD_UNCHANGED)
        rows,cols = img.shape
        sum = 0
        counter = 0 
        for i in range(0,rows):
            for j in range(0,cols):
                if(pd.isna(img[i,j])==False):
                    sum = sum + float(img[i,j])
                    counter = counter + 1
        VI = sum/counter
        print("VI = ", VI)
        # regression equation 
        # x is the VI of the whole image and y is the output, the calculated salinity
        y = (-8.6789) * VI + 1.2199
        SD = 0.106193235
        range_min = round((y - SD),4)
        range_max = round((y + SD),4)
        # result of the salinity... 
        print("Int1 calculated...")
        # print("Salinity of the image = [ " + str(range_min) + " - " + str(range_max) + " ]") # enable this if you want to see the real salinity values (either positive or negative) 
         
        global REAL_TIME_INFORMATION_STRING  
        if( ((range_min > 0) or (range_min ==0)) and ((range_max > 0) or (range_max ==0)) ):
            REAL_TIME_INFORMATION_STRING = "Int1 calculated. Salinity of the image = [ " + str(range_min) + " - " + str(range_max) + " ] dS/m"
            self.w = Show_Real_Time_Information()
            self.w.show()
        elif( (range_min < 0) and ((range_max > 0) or (range_max ==0)) ):
            REAL_TIME_INFORMATION_STRING = "Int1 calculated. Salinity of the image = [ 0 - " + str(range_max) + " ] dS/m"
            self.w = Show_Real_Time_Information()
            self.w.show()
        if((range_min < 0) and (range_max < 0)):
            REAL_TIME_INFORMATION_STRING = "Int1 calculated. Salinity cannot be calculated. Please use one of the other methods..."
            self.w = Show_Real_Time_Information()
            self.w.show()
    
    def calculate_Intensity_index_Int2(self):
        print("Calculating Salinity Index Int2...")
        import rasterio, os
        import cv2
        import numpy as np
        import pandas as pd
         
        with rasterio.open(self.UAV_REFLECTANCE_image_path) as f:
            profile = f.profile
            green = f.read(1)
            red = f.read(2)
            rededge = f.read(3)
            nir = f.read(4)
        result = (green + red + nir)/2
        tiff.imwrite('IMAGES/' + self.splitted_word_before_full_stop_REF + '_REFLECTANCE_Int2.tif', result, photometric='rgb') 
        self.CURRENT_LEAF_AREA_INDEX_IMAGE = 'IMAGES/' + self.splitted_word_before_full_stop_REF + '_REFLECTANCE_Int2.tif'
             
        # here I calculate the VI of the image....
        img = cv2.imread(self.CURRENT_LEAF_AREA_INDEX_IMAGE, cv2.IMREAD_UNCHANGED)
        rows,cols = img.shape
        sum = 0
        counter = 0 
        for i in range(0,rows):
            for j in range(0,cols):
                if(pd.isna(img[i,j])==False):
                    sum = sum + float(img[i,j])
                    counter = counter + 1
        VI = sum/counter
        print("VI = ", VI)
        # regression equation 
        # x is the VI of the whole image and y is the output, the calculated salinity
        y = (-3.3747) * VI + 1.4396
        SD = 0.217459279
        range_min = round((y - SD),4)
        range_max = round((y + SD),4)
        # result of the salinity... 
        print("Int2 calculated...")
        #print("Salinity of the image = [ " + str(range_min) + " - " + str(range_max) + " ]") # enable this if you want to see the real salinity values (either positive or negative) 
         
        global REAL_TIME_INFORMATION_STRING  
        if( ((range_min > 0) or (range_min ==0)) and ((range_max > 0) or (range_max ==0)) ):
            REAL_TIME_INFORMATION_STRING = "Int2 calculated. Salinity of the image = [ " + str(range_min) + " - " + str(range_max) + " ] dS/m"
            self.w = Show_Real_Time_Information()
            self.w.show()
        elif( (range_min < 0) and ((range_max > 0) or (range_max ==0)) ):
            REAL_TIME_INFORMATION_STRING = "Int2 calculated. Salinity of the image = [ 0 - " + str(range_max) + " ] dS/m"
            self.w = Show_Real_Time_Information()
            self.w.show()
        if((range_min < 0) and (range_max < 0)):
            REAL_TIME_INFORMATION_STRING = "Int2 calculated. Salinity cannot be calculated. Please use one of the other methods..."
            self.w = Show_Real_Time_Information()
            self.w.show()
    
    def calculate_NDVI(self):
        print("Calculating NDVI...")
        import rasterio, os
        import cv2
        import numpy as np
        import pandas as pd
         
        with rasterio.open(self.UAV_REFLECTANCE_image_path) as f:
            profile = f.profile
            green = f.read(1)
            red = f.read(2)
            rededge = f.read(3)
            nir = f.read(4)
        result = (nir - red)/(nir + red)
        tiff.imwrite('IMAGES/' + self.splitted_word_before_full_stop_REF + '_REFLECTANCE_NDVI.tif', result, photometric='rgb') # here
        self.CURRENT_LEAF_AREA_INDEX_IMAGE = 'IMAGES/' + self.splitted_word_before_full_stop_REF + '_REFLECTANCE_NDVI.tif'
                 
        # here I calculate the VI of the image....
        img = cv2.imread(self.CURRENT_LEAF_AREA_INDEX_IMAGE, cv2.IMREAD_UNCHANGED)
        rows,cols = img.shape
        sum = 0
        counter = 0 
        for i in range(0,rows):
            for j in range(0,cols):
                if(pd.isna(img[i,j])==False):
                    sum = sum + float(img[i,j])
                    counter = counter + 1
        VI = sum/counter
        print("VI = ", VI)
        # regression equation 
        # x is the VI of the whole image and y is the output, the calculated salinity
        y = 1.7101 * VI - 0.6037
        SD = 0.084888068
        range_min = round((y - SD),4)
        range_max = round((y + SD),4)
        # result of the salinity... 
        print("NDVI calculated...")
        #print("Salinity of the image = [ " + str(range_min) + " - " + str(range_max) + " ]") # enable this if you want to see the real salinity values (either positive or negative) 
         
        global REAL_TIME_INFORMATION_STRING  
        if( ((range_min > 0) or (range_min ==0)) and ((range_max > 0) or (range_max ==0)) ):
            REAL_TIME_INFORMATION_STRING = "NDVI calculated. Salinity of the image = [ " + str(range_min) + " - " + str(range_max) + " ] dS/m"
            self.w = Show_Real_Time_Information()
            self.w.show()
        elif( (range_min < 0) and ((range_max > 0) or (range_max ==0)) ):
            REAL_TIME_INFORMATION_STRING = "NDVI calculated. Salinity of the image = [ 0 - " + str(range_max) + " ] dS/m"
            self.w = Show_Real_Time_Information()
            self.w.show()
        if((range_min < 0) and (range_max < 0)):
            REAL_TIME_INFORMATION_STRING = "NDVI calculated. Salinity cannot be calculated. Please use one of the other methods..."
            self.w = Show_Real_Time_Information()
            self.w.show()
    
    def calculate_SAVI(self):
        print("Calculating SAVI...")
        import rasterio, os
        import cv2
        import numpy as np
        import pandas as pd
         
        with rasterio.open(self.UAV_REFLECTANCE_image_path) as f:
            profile = f.profile
            green = f.read(1)
            red = f.read(2)
            rededge = f.read(3)
            nir = f.read(4)
        L = 0.5
        
        result = (1+L) * ((nir - red)/(nir + red + L))
            
        tiff.imwrite('IMAGES/' + self.splitted_word_before_full_stop_REF + '_REFLECTANCE_SAVI.tif', result, photometric='rgb') # here
        self.CURRENT_LEAF_AREA_INDEX_IMAGE = 'IMAGES/' + self.splitted_word_before_full_stop_REF + '_REFLECTANCE_SAVI.tif'
         
        # here I calculate the VI of the image....
        img = cv2.imread(self.CURRENT_LEAF_AREA_INDEX_IMAGE, cv2.IMREAD_UNCHANGED)
        rows,cols = img.shape
        sum = 0
        counter = 0 
        for i in range(0,rows):
            for j in range(0,cols):
                if(pd.isna(img[i,j])==False):
                    sum = sum + float(img[i,j])
                    counter = counter + 1
        VI = sum/counter
        print("VI = ", VI)
        # regression equation 
        # x is the VI of the whole image and y is the output, the calculated salinity
        y = 2.3571 * VI - 0.5093
        SD = 0.102547704
        range_min = round((y - SD),4)
        range_max = round((y + SD),4)
        # result of the salinity... 
        print("SAVI calculated...")
        #print("Salinity of the image = [ " + str(range_min) + " - " + str(range_max) + " ]") # enable this if you want to see the real salinity values (either positive or negative) 
         
        global REAL_TIME_INFORMATION_STRING  
        if( ((range_min > 0) or (range_min ==0)) and ((range_max > 0) or (range_max ==0)) ):
            REAL_TIME_INFORMATION_STRING = "SAVI calculated. Salinity of the image = [ " + str(range_min) + " - " + str(range_max) + " ] dS/m"
            self.w = Show_Real_Time_Information()
            self.w.show()
        elif( (range_min < 0) and ((range_max > 0) or (range_max ==0)) ):
            REAL_TIME_INFORMATION_STRING = "SAVI calculated. Salinity of the image = [ 0 - " + str(range_max) + " ] dS/m"
            self.w = Show_Real_Time_Information()
            self.w.show()
        if((range_min < 0) and (range_max < 0)):
            REAL_TIME_INFORMATION_STRING = "SAVI calculated. Salinity cannot be calculated. Please use one of the other methods..."
            self.w = Show_Real_Time_Information()
            self.w.show()
            
    def calculate_MSAVI2(self):
        print("Calculating MSAVI2...")
        import rasterio, os
        import cv2
        import numpy as np
        import pandas as pd
        def msavi2(red,nearinfrared):
            import math 
            return (2*nearinfrared+1 - np.math.sqrt(((2*nearinfrared+1)**2)-8*(nearinfrared-red)))/2
         
        with rasterio.open(self.UAV_REFLECTANCE_image_path) as f:
            profile = f.profile
            green = f.read(1)
            red = f.read(2)
            rededge = f.read(3)
            nir = f.read(4)
        my_MSAVI2_function = np.vectorize(msavi2)
        result = my_MSAVI2_function(red, nir)
        tiff.imwrite('IMAGES/' + self.splitted_word_before_full_stop_REF + '_REFLECTANCE_MSAVI2.tif', result, photometric='rgb') 
        self.CURRENT_LEAF_AREA_INDEX_IMAGE = 'IMAGES/' + self.splitted_word_before_full_stop_REF + '_REFLECTANCE_MSAVI2.tif'
         
        # here I calculate the VI of the image....
        img = cv2.imread(self.CURRENT_LEAF_AREA_INDEX_IMAGE, cv2.IMREAD_UNCHANGED)
        rows,cols = img.shape
        sum = 0
        counter = 0 
        for i in range(0,rows):
            for j in range(0,cols):
                if(pd.isna(img[i,j])==False):
                    sum = sum + float(img[i,j])
                    counter = counter + 1
        VI = sum/counter
        print("VI = ", VI)
        # regression equation 
        # x is the VI of the whole image and y is the output, the calculated salinity
        y = 1.9539 * VI - 0.3395
        SD = 0.102035993
        range_min = round((y - SD),4)
        range_max = round((y + SD),4)
        # result of the salinity... 
        print("MSAVI2 calculated...")
        # print("Salinity of the image = [ " + str(range_min) + " - " + str(range_max) + " ]") # enable this if you want to see the real salinity values (either positive or negative) 
                 
        global REAL_TIME_INFORMATION_STRING  
        if( ((range_min > 0) or (range_min ==0)) and ((range_max > 0) or (range_max ==0)) ):
            REAL_TIME_INFORMATION_STRING = "MSAVI2 calculated. Salinity of the image = [ " + str(range_min) + " - " + str(range_max) + " ] dS/m"
            self.w = Show_Real_Time_Information()
            self.w.show()
        elif( (range_min < 0) and ((range_max > 0) or (range_max ==0)) ):
            REAL_TIME_INFORMATION_STRING = "MSAVI2 calculated. Salinity of the image = [ 0 - " + str(range_max) + " ] dS/m"
            self.w = Show_Real_Time_Information()
            self.w.show()
        if((range_min < 0) and (range_max < 0)):
            REAL_TIME_INFORMATION_STRING = "MSAVI2 calculated. Salinity cannot be calculated. Please use one of the other methods..."
            self.w = Show_Real_Time_Information()
            self.w.show()
        
    def calculate_RENDVI(self):
        print("Calculating RENDVI...")
        
        import rasterio, os
        import cv2
        import numpy as np
        import pandas as pd
         
        with rasterio.open(self.UAV_REFLECTANCE_image_path) as f:
            profile = f.profile
            green = f.read(1)
            red = f.read(2)
            rededge = f.read(3)
            nir = f.read(4)
        result = (nir - rededge) / (nir + rededge)
        tiff.imwrite('IMAGES/' + self.splitted_word_before_full_stop_REF + '_REFLECTANCE_RENDVI.tif', result, photometric='rgb') 
        self.CURRENT_LEAF_AREA_INDEX_IMAGE = 'IMAGES/' + self.splitted_word_before_full_stop_REF + '_REFLECTANCE_RENDVI.tif'
            
        # here I calculate the VI of the image....
        img = cv2.imread(self.CURRENT_LEAF_AREA_INDEX_IMAGE, cv2.IMREAD_UNCHANGED)
        rows,cols = img.shape
        sum = 0
        counter = 0 
        for i in range(0,rows):
            for j in range(0,cols):
                if(pd.isna(img[i,j])==False):
                    sum = sum + float(img[i,j])
                    counter = counter + 1
        VI = sum/counter
        print("VI = ", VI)
        # regression equation 
        # x is the VI of the whole image and y is the output, the calculated salinity
        y = 7.384 * VI - 0.2384
        SD = 0.134621988
        range_min = round((y - SD),4)
        range_max = round((y + SD),4)
        # result of the salinity... 
        print("RENDVI calculated...")
        #print("Salinity of the image = [ " + str(range_min) + " - " + str(range_max) + " ]") # enable this if you want to see the real salinity values (either positive or negative) 
                 
        global REAL_TIME_INFORMATION_STRING  
        if( ((range_min > 0) or (range_min ==0)) and ((range_max > 0) or (range_max ==0)) ):
            REAL_TIME_INFORMATION_STRING = "RENDVI calculated. Salinity of the image = [ " + str(range_min) + " - " + str(range_max) + " ] dS/m"
            self.w = Show_Real_Time_Information()
            self.w.show()
        elif( (range_min < 0) and ((range_max > 0) or (range_max ==0)) ):
            REAL_TIME_INFORMATION_STRING = "RENDVI calculated. Salinity of the image = [ 0 - " + str(range_max) + " ] dS/m"
            self.w = Show_Real_Time_Information()
            self.w.show()
        if((range_min < 0) and (range_max < 0)):
            REAL_TIME_INFORMATION_STRING = "RENDVI calculated. Salinity cannot be calculated. Please use one of the other methods..."
            self.w = Show_Real_Time_Information()
            self.w.show()
                    
    def S6_equation(self):
        from PyQt5 import QtGui, QtWidgets
        print("S6_equation...")
        dialog = QtWidgets.QDialog()
        lay = QtWidgets.QVBoxLayout(dialog)
        label = QtWidgets.QLabel()
        lay.addWidget(label)    
        pixmap = QtGui.QPixmap("EQUATIONS_IMAGES/S6.jpg")
        label.setPixmap(pixmap)
        dialog.exec_()    

    def SI_equation(self):
        from PyQt5 import QtGui, QtWidgets
        print("SI_equation...")
        dialog = QtWidgets.QDialog()
        lay = QtWidgets.QVBoxLayout(dialog)
        label = QtWidgets.QLabel()
        lay.addWidget(label)
        pixmap = QtGui.QPixmap("EQUATIONS_IMAGES/SI.jpg")
        label.setPixmap(pixmap)
        dialog.exec_()

    def SI4_equation(self):
        from PyQt5 import QtGui, QtWidgets
        print("SI4_equation...")
        dialog = QtWidgets.QDialog()
        lay = QtWidgets.QVBoxLayout(dialog)
        label = QtWidgets.QLabel()
        lay.addWidget(label)
        pixmap = QtGui.QPixmap("EQUATIONS_IMAGES/SI4.jpg")
        label.setPixmap(pixmap)
        dialog.exec_()

    def Int1_equation(self): 
        from PyQt5 import QtGui, QtWidgets
        print("Int1_equation...")
        dialog = QtWidgets.QDialog()
        lay = QtWidgets.QVBoxLayout(dialog)
        label = QtWidgets.QLabel()
        lay.addWidget(label)
        pixmap = QtGui.QPixmap("EQUATIONS_IMAGES/INT1.jpg")
        label.setPixmap(pixmap)
        dialog.exec_()
    
    def Int2_equation(self): 
        from PyQt5 import QtGui, QtWidgets
        print("Int2_equation...")
        dialog = QtWidgets.QDialog()
        lay = QtWidgets.QVBoxLayout(dialog)
        label = QtWidgets.QLabel()
        lay.addWidget(label)
        pixmap = QtGui.QPixmap("EQUATIONS_IMAGES/INT2.jpg")
        label.setPixmap(pixmap)
        dialog.exec_()

    def NDVI_equation(self): 
        from PyQt5 import QtGui, QtWidgets
        print("NDVI_equation...")
        dialog = QtWidgets.QDialog()
        lay = QtWidgets.QVBoxLayout(dialog)
        label = QtWidgets.QLabel()
        lay.addWidget(label)
        pixmap = QtGui.QPixmap("EQUATIONS_IMAGES/NDVI.jpg")
        label.setPixmap(pixmap)
        dialog.exec_()

    def SAVI_equation(self):
        from PyQt5 import QtGui, QtWidgets
        print("SAVI_equation...")
        dialog = QtWidgets.QDialog()
        lay = QtWidgets.QVBoxLayout(dialog)
        label = QtWidgets.QLabel()
        lay.addWidget(label)
        pixmap = QtGui.QPixmap("EQUATIONS_IMAGES/SAVI.jpg")
        label.setPixmap(pixmap)
        dialog.exec_()
        
    def MSAVI2_equation(self):
        from PyQt5 import QtGui, QtWidgets
        print("MSAVI2...")
        dialog = QtWidgets.QDialog()
        lay = QtWidgets.QVBoxLayout(dialog)
        label = QtWidgets.QLabel()
        lay.addWidget(label)
        pixmap = QtGui.QPixmap("EQUATIONS_IMAGES/MSAVI2.jpg")
        label.setPixmap(pixmap)
        dialog.exec_() 
        
    def RENDVI_equation(self):
        from PyQt5 import QtGui, QtWidgets
        print("RENDVI...")
        dialog = QtWidgets.QDialog()
        lay = QtWidgets.QVBoxLayout(dialog)
        label = QtWidgets.QLabel()
        lay.addWidget(label)
        pixmap = QtGui.QPixmap("EQUATIONS_IMAGES/RENDVI.jpg")
        label.setPixmap(pixmap)
        dialog.exec_() 
        
    def clean_data_folder(self, checked):
        import os, shutil
        folder_to_delete_contents = 'IMAGES'
        for content in os.listdir(folder_to_delete_contents):
            path_of_the_file = os.path.join(folder_to_delete_contents, content)
            try:
                if os.path.isfile(path_of_the_file) or os.path.islink(path_of_the_file):
                    os.unlink(path_of_the_file)
                elif os.path.isdir(path_of_the_file):
                    shutil.rmtree(path_of_the_file)
            except Exception as e:
                print('Cannot delete %s. Because: %s' % (path_of_the_file, e))        
    
        
    def show_real_time_info(self, checked):
        print("Real time info...")
        self.w = Show_Real_Time_Information()
        self.w.show()
            
if __name__ == "__main__":
    app = QApplication(sys.argv)
    icon = QIcon(os.path.join(selfDir, '_static', 'orthoview.ico'))
    app.setWindowIcon(icon)

    window = OrthoView()
    window.show()
    sys.exit(app.exec_())
