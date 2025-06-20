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
import weakref
import pandas as pd
import numpy as np

#Qgis imports
from qgis.core import QgsVectorLayer, Qgis, QgsProject, QgsLogger, QgsMessageLog, QgsMapLayer
from qgis.gui import QgisInterface, QgsMapLayerComboBox, QgsFieldComboBox

#pyQt
from PyQt5.QtWidgets import (
    QFileDialog, QGroupBox, QComboBox, QTableWidgetItem, QWidget, QTableWidget,QDoubleSpinBox, QHeaderView,
    QListView
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
 
                 iface:        "QgisInterface | None"        = None,
                 statusQlab   = None,
                 parent:       "QtCore.QObject | None"       = None,
                 log_nm:       str | None                    = None,
                 debug_logger: "logging.Logger | None"       = None):
        """
        Parameters
        ----------
        iface : QgisInterface, optional
            QGIS interface so we can push/popup messages.
        statusQlab : QLabel, optional
            A status-line QLabel that mirrors log messages.
        parent : QObject, optional
            Widget that owns this logger (not used for pytest hierarchy).
        log_nm : str, optional
            Public prefix (e.g. “MD”).  If omitted we derive one.
        debug_logger : logging.Logger, optional
            Root pytest logger; unit tests capture plugin output here.
        """

        # ------------------------- QGIS handles ------------------------
        if iface is not None and "QgisInterface" not in str(type(iface)):
            raise IOError(f"bad type on iface: {type(iface)}")

        self.iface       = iface
        self.messageBar  = iface.messageBar() if iface else None
        self.statusQlab  = statusQlab
        self.parent      = parent

        # ------------------------- public prefix -----------------------
        if log_nm is None:
            # fall back to “cf2” or “cf2.<ClassName>”
            cls = parent.__class__.__name__ if parent else ""
            self.log_nm = f"{self.log_nm_default}.{cls}" if cls else self.log_nm_default
        else:
            self.log_nm = log_nm

        # --------------------- pytest/file hierarchy -------------------
        #
        # Mirror every segment of self.log_nm exactly once in the
        # debug_logger’s dotted name, nothing else.
        #
        if debug_logger is not None:
            for seg in self.log_nm.split("."):
                if seg and seg not in debug_logger.name.split("."):
                    debug_logger = debug_logger.getChild(seg)

        self.debug_logger = debug_logger
    # ------------------------------------------------------------------ #
    #  getChild                                                          #
    # ------------------------------------------------------------------ #
    def getChild(self, new_childnm: str, *, child_parent=None):
        """
        Return a child logger with prefix ``<self.log_nm>.<new_childnm>``.

        No dialog class names are injected; the pytest hierarchy is
        extended with *only* the new segment.
        """
        child_log_nm = f"{self.log_nm}.{new_childnm}"

        return plugLogger(
            iface=self.iface,
            statusQlab=self.statusQlab,
            parent=child_parent,          # keep None unless you *want* cls name
            log_nm=child_log_nm,
            debug_logger=self.debug_logger,   # __init__ will append missing seg
        )
    
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
        if push and not self.iface is None:
            try:
                #self.messageBar.pushMessage(self.log_tabnm, msg_raw, level=qlevel)
                self.messageBar.pushMessage(msg_raw, level=qlevel)
            except Exception as e:
                raise IOError(f'failed to push message to interface\n    {self.iface}\n    {e}')
                #QgsLogger.debug(f'failed to push message to interface\n    {self.iface}\n    {e}') #used for standalone tests
        
        #Optional widget
        if status or push:
            if not self.statusQlab is None:
                self.statusQlab.setText(msg_raw)
    

#===============================================================================
# WIDGET binds-------------
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
            
def bind_tableWidget(widget, logger, iface=None, widget_type_d=dict()):
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
    
    def set_df_to_QTableWidget_spinbox(df):
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
        
    
    def set_df_to_QTableWidget_strings(df):
        """
        Populate the QTableWidget with the contents of the DataFrame as strings.
        
        Parameters:
            widget (QTableWidget): The widget to populate.
            df (pandas.DataFrame): The DataFrame containing the data.
            logger (optional): A logging object for debug messages.
        
        Raises:
            TypeError: if df is not a pandas DataFrame.
        """
 
    
        if not isinstance(df, pd.DataFrame):
            raise TypeError("df must be a pandas DataFrame")
    
        # Clear current contents and set new dimensions.
        widget.clearContents()
        num_rows, num_cols = df.shape
        widget.setRowCount(num_rows)
        widget.setColumnCount(num_cols)
    
        # Set horizontal header labels from DataFrame columns.
        widget.setHorizontalHeaderLabels(list(df.columns))
    
        # Populate each cell with a string version of the DataFrame's value.
        cnt = 0
        for row in range(num_rows):
            for col in range(num_cols):
                cnt+=1
                value = df.iat[row, col]
                # Convert NaN values to an empty string.
                cell_text = "" if pd.isnull(value) else str(value)
                widget.setItem(row, col, QTableWidgetItem(cell_text))
                
        log.debug(f'Updated QTableWidget with {cnt} cells')
        
    
    def clear_tableWidget(*args):
        """
        Fully clear a QTableWidget by removing all items, cell widgets, and header labels.
        
        Parameters:
            widget (QTableWidget): The QTableWidget instance to clear.
            logger (optional): A logging object for debugging (if provided).
        
        Returns:
            None
        """
        # If a logger is provided, get a child logger for this operation.
        if logger:
            log = logger.getChild('clear_tableWidget')
        else:
            log = None
    
        # Remove all cell widgets from the table.
        for row in range(widget.rowCount()):
            for col in range(widget.columnCount()):
                if widget.cellWidget(row, col) is not None:
                    widget.removeCellWidget(row, col)
    
        # Clear all items and header labels.
        widget.clear()
        # Reset the row and column counts to zero to fully remove the layout.
        widget.setRowCount(0)
        widget.setColumnCount(0)
        
 

    # Bind the helper methods to the widget for later use.
    widget.get_df_from_QTableWidget = get_df_from_QTableWidget
    widget.get_axis_labels = get_axis_labels
    widget.set_df_to_QTableWidget_spinbox=set_df_to_QTableWidget_spinbox
    widget.clear_tableWidget = clear_tableWidget
    widget.set_df_to_QTableWidget_strings=set_df_to_QTableWidget_strings

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
        
    def clear_view(self):
        """
        Remove **all** rows from the model so the QListView appears blank.
        Useful when you switch projects or want to reset the UI.
        """
        self.model().clear()
        # Optional: force an immediate repaint
        self.viewport().update()
        
 
    def get_selected_layers(self):
        """get the selected layers from the list widget"""
        qproj = QgsProject.instance()

        items = self.model().get_checked() #names of layers checked by user
        nms_l = [item.text() for item in items]
        
        assert len(nms_l)>0, 'layersListWidget has no layers selected!'
        
        
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
                  'get_selected_layers', 'clear_checks','check_all', 'check_byName', 'clear_view']:
        setattr(widget, fName, types.MethodType(eval(fName), widget)) 
        
        
def bind_simpleListWidget(widget, logger=None):
    """
    Bind a QTableView (or a QTableWidget using a model) to additional methods for DataFrame handling 
    and row selection via checkboxes. Uses a ListModel (a QStandardItemModel subclass) as the model.
 
    """
    
    assert isinstance(widget, QListView)
    # Ensure the widget uses our custom ListModel instance.
    # (ListModel should be defined elsewhere as a subclass of QStandardItemModel)
    if not hasattr(widget, "model") or widget.model() is None:
        # Create and set a new ListModel instance.
        widget.setModel(ListModel())
        
    widget.logger = logger

    def set_data(self, data_l):
        """
 
        """
        assert isinstance(data_l,list)
        
        model = self.model()
        model.clear()
        
        #retrieve
        # Set header labels; prepend a "Select" header for the checkboxes.
        
        model.add_checkable_data([QStandardItem(l) for l in data_l])
        #=======================================================================
        # headers = ["Select"] + list(df.columns)
        # model.setHorizontalHeaderLabels(headers)
        # 
        # # Populate each row.
        # for row_idx, (_, row) in enumerate(df.iterrows()):
        #     row_items = []
        #     # First column: checkable item.
        #     chk_item = QStandardItem()
        #     chk_item.setCheckable(True)
        #     chk_item.setCheckState(Qt.Unchecked)
        #     row_items.append(chk_item)
        #     # Remaining columns: string representations.
        #     for col in df.columns:
        #         cell_value = row[col]
        #         text = "" if pd.isnull(cell_value) else str(cell_value)
        #         row_items.append(QStandardItem(text))
        #     model.appendRow(row_items)
        #=======================================================================
        
 
        self.logger.debug(f"Populated model with {len(data_l)} rows")
    
 
    
    def check_byName(self, names_l):
        self.model().set_checked_byVal(names_l) 
                
    def clear_checks(self):
        self.model().set_checked_all()
        
            
    def check_all(self):
        self.model().set_checked_all(state=Qt.Checked)
        
    def get_checked_items(self):
        items = self.model().get_checked() #names of layers checked by user
        #retrieve a list of strings from the QStandrrdItems
        return [item.text() for item in items]
    
    # Bind the helper methods to the widget.
    widget.set_data = types.MethodType(set_data, widget)
    widget.get_checked_items = types.MethodType(get_checked_items, widget)
    widget.clear_checks = types.MethodType(clear_checks, widget)
    widget.check_all = types.MethodType(check_all, widget)
    widget.check_byName = types.MethodType(check_byName, widget)
    
    return widget

        
        
def bind_MapLayerComboBox(widget, #
                          iface=None, layerType=None):
    """
    add some bindings to layer combo boxes
    """
    assert isinstance(widget, QgsMapLayerComboBox)
    widget.iface=iface
    #default selection
    if not layerType is None:
        widget.setFilters(layerType)
    widget.setAllowEmptyLayer(True)
    widget.setCurrentIndex(-1) #set selection to none
    
    
    
    #===========================================================================
    # define new methods
    #===========================================================================

    def set_layer_by_name(layer_name: str) -> QgsMapLayer:
        """
        Retrieve a QgsMapLayer object from the current QGIS project using the layer's name.
    
        not using layerID as this does not persist between sessions
        """
        assert isinstance(layer_name, str), f"layer_name must be a string, not {type(layer_name)}"
    
        qproj = QgsProject.instance()
        
        layers_l = [layer for layer in qproj.mapLayers().values()]
        assert len(layers_l) > 0, "failed to find any layers in project"
    
        layers = [layer for layer in layers_l if layer.name() == layer_name]
        assert len(layers) > 0, f"failed to find any layers with name '{layer_name}' in project"
    
        if len(layers) > 1:
            raise KeyError(f"Multiple layers with name '{layer_name}' found in the project")
    
        layer = layers[0]
        widget.setLayer(layer)
        return layer

            
    #===========================================================================
    # bind functions
    #===========================================================================
    
    widget.set_layer_by_name = set_layer_by_name
    
    
def bind_QgsFieldComboBox(widget, signal_emitter_widget=None,   fn_str=None, fn_no_str=None):
    """bind some methods to a QgsFieldComboBox
    
    
    Parameters
    ----------
    widget : QgsFieldComboBox
        The combo box to bind methods to.
        
    signal_emitter_widget : QgsMapLayerComboBox, optional
    
        A QgsMapLayerComboBox instance that emits a signal when the layer changes.
        
    fn_str : str, optional
        A substring to match field names against. If provided, only fields containing this substring will be selected.

    """
 
    #widget.signal_emitter_widget=signal_emitter_widget
    # Ensure the widget is a QgsFieldComboBox.
    assert isinstance(widget, QgsFieldComboBox), f"Expected QgsFieldComboBox, got {type(widget)}"
    
    wref    = weakref.ref(widget)
    
    def _setLayer_fallback(self, layer=None):
        """
        Slot that selects an appropriate field whenever the layer changes.
        It is a *bound method*, so 'self' is the combo box (a QObject).
        
        """
        
        w = wref()                        # dereference weak-ref
        if w is None:
            # Combo box has been destroyed — disconnect once, then vanish
            try:
                signal_emitter_widget.layerChanged.disconnect(_setLayer_fallback)                    
            except (RuntimeError, TypeError):
                pass
            return
 
        
        # If signal passes in a layer, use it; otherwise look at emitter.
        if layer is None:
            layer = signal_emitter_widget.currentLayer()

        if layer is None:
            self.clear()
            return

        assert isinstance(layer, QgsVectorLayer)

        self.setLayer(layer)          # repopulate the list

        # pick the field to select …
        match = None
        for fld in layer.fields():
            if fn_no_str and fld.name() == fn_no_str:
                continue
            if fn_str and fn_str not in fld.name():
                continue
            match = fld.name()
            break

        if match:
            self.setField(match)

    # attach as a *method* so Qt sees 'self' === widget (a QObject)
    widget.setLayer_fallback = types.MethodType(_setLayer_fallback, widget)
    
    # If a signal emitter widget is provided, connect its layer-changed signal.
    if signal_emitter_widget is not None:
        assert isinstance(signal_emitter_widget, QgsMapLayerComboBox), f'Expected QgsMapLayerComboBox, got {type(signal_emitter_widget)}'
        # Assumes that the signal is named "currentLayerChanged" and emits a layer. 
        signal_emitter_widget.layerChanged.connect(widget.setLayer_fallback)
        
        # --- prime the combo immediately ---------------------------------------
        widget.setLayer_fallback()
        
    def connect_downstream_combobox(downstream_combo: QgsFieldComboBox):
        """
        Keep `downstream_combo` in lock-step with `widget` (the upstream combo).
        The downstream combo is disabled so the user can’t alter it.
     
        Parameters
        ----------
        downstream_combo : QgsFieldComboBox
            The combo box to mirror.
        """
        assert isinstance(downstream_combo, QgsFieldComboBox), (
            f"Expected QgsFieldComboBox, got {type(downstream_combo)}"
        )
     
        # Disable direct user interaction
        downstream_combo.setEnabled(False)
     
        # ---------- internal sync routine ----------
        def _sync():
            try:
                # 1. Mirror the layer (repopulates the downstream combo)
                downstream_combo.setLayer(widget.layer())
         
                # 2. Mirror the current field
                fld = widget.currentField()          # QgsFieldComboBox convenience
                if fld:                              # fld is a string or None
                    downstream_combo.setField(fld)
            except:
                #raise a QGIS warning
                QgsMessageLog.logMessage(
                    "Failed to sync downstream combo box",
                    level=Qgis.Warning
                )
                 
                 
        # -------------------------------------------
     
        # Hook up both relevant upstream signals
        #widget.layerChanged.connect(_sync)
        widget.fieldChanged.connect(_sync)
     
        # Do one initial sync so the downstream starts in the right state
        _sync()
         
    widget.connect_downstream_combobox = connect_downstream_combobox
 
        
        
        
def get_layer_info_from_combobox(combo):
    """
    Retrieve the layer name and layer ID from a QgsMapLayerComboBox.
 
    """
    layer = combo.currentLayer()
    if layer is None:
        return None, None
    else:
        return layer.name(), layer.id()
    





