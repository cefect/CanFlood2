'''
Created on Apr. 29, 2024

@author: cef

QGIS plugin helpers
'''

#===============================================================================
# imports-----
#===============================================================================
#python
import logging, configparser, datetime, sys, os, types
import pandas as pd
import numpy as np

#Qgis imports
from qgis.core import QgsVectorLayer, Qgis, QgsProject, QgsLogger, QgsMessageLog, QgsMapLayer
from qgis.gui import QgisInterface

#pyQt
from PyQt5.QtWidgets import QFileDialog, QGroupBox, QComboBox, QTableWidgetItem, QWidget
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtCore import Qt, QAbstractTableModel, QObject
from PyQt5 import QtCore

#===============================================================================
# classes------
#===============================================================================
class plugLogger(object): 
    """pythonic logging interface"""
    
    log_tabnm = 'CanCurve' # qgis logging panel tab name
    
    log_nm = 'cc' #logger name
    
    def __init__(self, 
                 iface,
                 statusQlab=None,                 
                 parent=None,
                 log_nm = None,
                 debug_logger=None,
                 ):
        """
        
        params
        ---------
        debug_logger: python logging class
            workaround to capture QgsLogger
        """
        
        self.iface=iface
        self.statusQlab = statusQlab
        self.parent=parent
        self.debug_logger=debug_logger
        
        if  log_nm is None: #normal calls
            self.log_nm = '%s.%s'%(self.log_nm, self.parent.__class__.__name__)
        else: #getChild calls
            self.log_nm = log_nm
        
        
    def getChild(self, new_childnm):
        
        if hasattr(self.parent, 'logger'):
            log_nm = '%s.%s'%(self.parent.logger.log_nm, new_childnm)
        else:
            log_nm = new_childnm
        
        #build a new logger
        child_log = plugLogger(self.parent, 
                           statusQlab=self.statusQlab,
                           log_nm=log_nm,
                           debug_logger=self.debug_logger)
        

        
        return child_log
    
    def info(self, msg):
        self._loghlp(msg, Qgis.Info, push=False, status=True)


    def debug(self, msg):
        self._loghlp(msg, -1, push=False, status=False)
        
        if not self.debug_logger is None: 
            self.debug_logger.debug(msg)
 
    def warning(self, msg):
        self._loghlp(msg, Qgis.Warning, push=False, status=True)

    def push(self, msg):
        self._loghlp(msg, Qgis.Info, push=True, status=True)

    def error(self, msg):
        """similar behavior to raising a QError.. but without throwing the execption"""
        self._loghlp(msg, Qgis.Critical, push=True, status=True)
        
    def _loghlp(self, #helper function for generalized logging
                msg_raw, qlevel, 
                push=False, #treat as a push message on Qgis' bar
                status=False, #whether to send to the status widget
                ):
        """
        QgsMessageLog writes to the message panel
            optionally, users can enable file logging
            this file logger 
        """

        #=======================================================================
        # send message based on qlevel
        #=======================================================================
        msgDebug = '%s    %s: %s'%(datetime.datetime.now().strftime('%d-%H.%M.%S'), self.log_nm,  msg_raw)
        
        if qlevel < 0: #file logger only            
            QgsLogger.debug('D_%s'%msgDebug)            
            push, status = False, False #should never trip
            
        else:#console logger
            msg = '%s:   %s'%(self.log_nm, msg_raw)
            QgsMessageLog.logMessage(msg, self.log_tabnm, level=qlevel)
            QgsLogger.debug('%i_%s'%(qlevel, msgDebug)) #also send to file
            
        #Qgis bar
        if push:
            try:
                self.iface.messageBar().pushMessage(self.log_tabnm, msg_raw, level=qlevel)
            except:
                QgsLogger.debug('failed to push to interface') #used for standalone tests
        
        #Optional widget
        if status or push:
            if not self.statusQlab is None:
                self.statusQlab.setText(msg_raw)
    

#===============================================================================
# widget binds-------------
#===============================================================================
class ListModel(QStandardItemModel): #wrapper for list functions with check boxes
    
    def add_checkable_data(self, data_l):
        
        for item in data_l:
            item.setCheckable(True)
            item.setCheckState(Qt.Unchecked)
            self.appendRow(item)
            
    def get_items(self):
        return [self.item(i) for i in range(self.rowCount())]
    def get_checked(self, state=Qt.Checked): #retrieve all items taht are checked
        return [i for i in self.get_items() if i.checkState()==state]

    def set_checked_byVal(self, val_l): #assign check state to items based on those matching the values
        for item in self.get_items():
            if item.text() in val_l:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
                
    def set_checked_all(self, state=Qt.Unchecked):
        for item in self.get_items():
            item.setCheckState(state)
            
def bind_layersListWidget(widget, #instanced widget
                          log,
                          layerType=None, #optional layertype to enforce
                          iface=None,
                          
                         ):
    """bind a layersListWidget to a widget and add some methods
    because Qgis passes instanced widgets, need to bind any new methods programatically
    """
    #assert not iface is None
        
    widget.iface = iface
    widget.layerType = layerType
    widget.setModel(ListModel())
    
    #===========================================================================
    # populating and setting selection
    #===========================================================================
    def populate_layers(self, layers=None):
        """refresh the list with layers"""
        if layers is None:
            #get all from the project
            layers = [layer for layer in QgsProject.instance().mapLayers().values()]
            
            #apply filters
            if not self.layerType is None:
                layers = self._apply_filter(layers)
                
        
        assert isinstance(layers, list), 'bad type on layeres: %s'%type(layers)
        model = self.model()
        
        model.clear()
        
        model.add_checkable_data([QStandardItem(l.name()) for l in layers])

            
    def _apply_filter(self, layers):
        return [rl for rl in layers if rl.type()==self.layerType]
            
    def select_visible(self):
        #print('selecint only visible layers')
        lays_l = self.iface.mapCanvas().layers()
        self.model().set_checked_byVal([l.name() for l in lays_l])
        
    def select_canvas(self):
 
        lays_l = self.iface.layerTreeView().selectedLayers()
        #log.info('setting selection to %i layers from layerTreeView'%len(lays_l))
        self.model().set_checked_byVal([l.name() for l in lays_l])
        

    def clear_checks(self):
        self.model().set_checked_all()
        
            
    def check_all(self):
        self.model().set_checked_all(state=Qt.Checked)
        
    def check_byName(self, layName_l):
        self.model().set_checked_byVal(layName_l)
 
    def get_selected_layers(self):
        """get the selected layers from the list widget"""
        qproj = QgsProject.instance()

        items = self.model().get_checked() #names of layers checked by user
        nms_l = [item.text() for item in items]
        
        assert len(nms_l)>0, 'no selection!'
        
        
        #retrieve layers from canvas
        lays_d = {nm:qproj.mapLayersByName(nm) for nm in nms_l} 
        
        
        
        
        #check we only got one hit
        d = dict()
        for k,hits_all in lays_d.items():
            
            """when a raster and vector layer have the same name"""
            hits = self._apply_filter(hits_all) #remove any not matching the type
            
            
            assert not len(hits)>1, 'matched multiple layers for \'%s\'... layers need unique names'%k
            assert not len(hits)==0, 'failed to match any layers with \'%s\''%k
            
            lay = hits[0]
            assert isinstance(lay, QgsMapLayer), 'bad type on %s: %s'%(k, type(lay))
            
            d[k] = lay
        
        #drop to singular elements
        
        return d
        
        
    #===========================================================================
    # bind them
    #===========================================================================
    for fName in ['populate_layers', '_apply_filter', 'select_visible', 'select_canvas', 
                  'get_selected_layers', 'clear_checks','check_all', 'check_byName']:
        setattr(widget, fName, types.MethodType(eval(fName), widget)) 
      