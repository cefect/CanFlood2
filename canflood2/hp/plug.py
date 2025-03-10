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
from PyQt5.QtWidgets import (
    QFileDialog, QGroupBox, QComboBox, QTableWidgetItem, QWidget, QTableWidget,QDoubleSpinBox, QHeaderView
    )
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtCore import Qt, QAbstractTableModel, QObject
from PyQt5 import QtCore

#===============================================================================
# classes------
#===============================================================================
class plugLogger(object): 
    """pythonic logging interface"""
    
    log_tabnm = 'CanFlood2' # qgis logging panel tab name
    
    log_nm_default = 'cf2' #logger name
    
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
        
        #setup the name
        parentClassName = self.parent.__class__.__name__
        if 'None' in parentClassName:
            parentClassName = ''
        
        
        if  log_nm is None: #normal calls
            self.log_nm = '%s.%s'%(self.log_nm_default, parentClassName)

        else: #getChild calls
            self.log_nm = log_nm
            
        if not debug_logger is None:
            debug_logger = debug_logger.getChild(parentClassName)
            
 
        
        self.debug_logger=debug_logger
        
        
    def getChild(self, new_childnm):
        
        if hasattr(self.parent, 'logger'):
            log_nm = '%s.%s'%(self.parent.logger.log_nm, new_childnm)
        else:
            log_nm = new_childnm
            
        #configure debug logger
        try: #should only work during tests?
            debug_logger = self.debug_logger.getChild(new_childnm)
        except:
            debug_logger = None
        
        #build a new logger
        child_log = plugLogger(self.parent, 
                           statusQlab=self.statusQlab,
                           log_nm=log_nm,
                           debug_logger=debug_logger)
        

        
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
        cnt=0
        for item in self.get_items():
            if item.text() in val_l:
                item.setCheckState(Qt.Checked)
                cnt+=1
            else:
                item.setCheckState(Qt.Unchecked)
                
        assert cnt==len(val_l), f'failed to match  values ({len(val_l)}/{cnt}) in \n {val_l}'
                
    def set_checked_all(self, state=Qt.Unchecked):
        for item in self.get_items():
            item.setCheckState(state)
            
def bind_tableWidget(widget, logger, iface=None, table_column_type_d=dict()):
    """
    Bind custom methods to a QTableWidget.

    This function should be called during the initialization of your dialog.
    It attaches additional helper methods to the widget for tasks such as
    extracting the table contents as a pandas DataFrame.

    Parameters:
        widget (QTableWidget): The QTableWidget instance to enhance.
        logger: Logging object.
        iface: QGIS interface instance (optional).

    Returns:
        QTableWidget: The same widget with additional bound methods.
    """
 

    assert isinstance(widget, QTableWidget), "widget must be an instance of QTableWidget"
    widget.iface = iface
    log = logger.getChild('bind_tableWidget')

    def get_axis_labels(axis=0):
        """
        Retrieve axis labels from the bound QTableWidget.

        Parameters:
            axis (int): Axis for labels (0 for rows, 1 for columns).

        Returns:
            list: List of labels as strings.
        """
        if axis == 1:
            header_items = [widget.horizontalHeaderItem(col) for col in range(widget.columnCount())]
        elif axis == 0:
            header_items = [widget.verticalHeaderItem(row) for row in range(widget.rowCount())]
        else:
            raise ValueError("axis must be 0 (rows) or 1 (columns)")

        labels = []
        for item in header_items:
            labels.append(item.text() if item is not None else "Unnamed")
        return labels

    def get_df_from_QTableWidget():
        """
        Extract a pandas DataFrame from the contents of the bound QTableWidget.

        Returns:
            pandas.DataFrame: A DataFrame populated with the table's data.
        """

        # Retrieve column and row labels.
        columns = get_axis_labels(axis=1)
        rows = get_axis_labels(axis=0)
        df = pd.DataFrame(columns=columns, index=rows)
    
        for i in range(widget.rowCount()):
            for j in range(widget.columnCount()):
                # Try to retrieve a widget from the cell.
                cell_widget = widget.cellWidget(i, j)
                if cell_widget is not None:
                    # Check for QDoubleSpinBox to get a float value.
                    if isinstance(cell_widget, QDoubleSpinBox):
                        value = cell_widget.value()
                    # If the widget has a text() method, use that.
                    elif hasattr(cell_widget, 'text'):
                        value = cell_widget.text()
                    else:
                        value = None
                else:
                    # Otherwise, use the QTableWidgetItem's text.
                    item = widget.item(i, j)
                    value = item.text() if item is not None else None
    
                df.iloc[i, j] = value
    
        log.debug(f'Extracted dataframe {df.shape}')
        return df.reset_index(drop=True)
    
    def set_df_to_QTableWidget_spinbox(df, widget_type_d=dict()):
        """
        Populate the QTableWidget with the contents of the DataFrame using widget types
        defined in widget_type_d.
    
        The mapping widget_type_d specifies for each column:
          - 'type': either "string" (for text) or "spinbox" (for a QDoubleSpinBox)
          - 'locked': whether the column should be non-editable
    
        Additionally, the function:
          - Hides the fourth (last) column.
          - Sets the third column to expand.
        
        Parameters:
            df (pandas.DataFrame): The DataFrame containing the data.
            widget_type_d (dict): A dictionary mapping column indices to a dict with keys 'type' and 'locked'.
    
        Raises:
            TypeError: if df is not a pandas DataFrame.
        """
 
    
        if not isinstance(df, pd.DataFrame):
            raise TypeError("df must be a pandas DataFrame")
        
        # Clear the table and set its dimensions.
        widget.clearContents()
        num_rows, num_cols = df.shape
        widget.setRowCount(num_rows)
        widget.setColumnCount(num_cols)
        
        header_labels = df.copy().rename(columns={k: v['label'] for k, v in widget_type_d.items()}).columns.tolist()
        widget.setHorizontalHeaderLabels(header_labels)
        
        cnt = 0
        # Populate each cell.
        for row_index, row in df.iterrows():
            for col_index, col_name in enumerate(df.columns):
                # Retrieve column options from the mapping; default to string & unlocked if not provided.
                #col_opts = widget_type_d.get(col_index, {'widgetType': 'string', 'widgetLock': False})
                col_opts = widget_type_d[col_name]
                cell_type = col_opts.get('widgetType', 'string')
                locked = col_opts.get('widgetLock', False)
                cell_value = row.iloc[col_index]
                
                if not pd.isnull(cell_value):
                    cnt+=1
                
                if cell_type == "spinbox":
                    # Retrieve existing spinbox widget or create one.
                    spinbox = widget.cellWidget(row_index, col_index)
                    if spinbox is None:
                        spinbox = QDoubleSpinBox()
                        spinbox.setRange(0.0, 9999)
                        spinbox.setDecimals(5)
                        widget.setCellWidget(row_index, col_index, spinbox)
                    try:
                        spinbox.setValue(0.0 if pd.isnull(cell_value) else float(cell_value))
                    except (ValueError, TypeError):
                        spinbox.setValue(0.0)
                    # Lock the spinbox if specified.
                    if locked:
                        spinbox.setReadOnly(True)
                    
                     
                else:
                    # For text cells, create/update a QTableWidgetItem.
                    if pd.isnull(cell_value):
                        cell_value = ""
                    item = QTableWidgetItem(str(cell_value))
                    # Remove the editable flag if the cell should be locked.
                    if locked:
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    widget.setItem(row_index, col_index, item)
                
    
        # Configure header behavior:
        header = widget.horizontalHeader()
        # Set the third column (index 2) to expand.
        if num_cols >= 3:
            header.setSectionResizeMode(2, QHeaderView.Stretch)
        # Hide the fourth (last) column if present.
        
        for col_index, (col_name, widgetHide) in enumerate({k:v['widgetHide'] for k,v in widget_type_d.items()}.items()):
            if widgetHide:
                widget.setColumnHidden(col_index, True)
        
 
        
        log.debug(f'Updated QTableWidget with {cnt} cells')

    # Bind the helper methods to the widget for later use.
    widget.get_df_from_QTableWidget = get_df_from_QTableWidget
    widget.get_axis_labels = get_axis_labels
    widget.set_df_to_QTableWidget_spinbox=set_df_to_QTableWidget_spinbox

    return widget
    
    
            
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
        
        
        
        
        
        
        
        
        
def get_layer_info_from_combobox(combo):
    """
    Retrieve the layer name and layer ID from a QgsMapLayerComboBox.
 
    """
    layer = combo.currentLayer()
    if layer is None:
        return None, None
    else:
        return layer.name(), layer.id()
    





