# -*- coding: utf-8 -*-
"""
/***************************************************************************
 canfloodDialog
                                 A QGIS plugin
 Open source flood risk modelling toolbox for Canada v2
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2025-03-04
        git sha              : $Format:%H$
        copyright            : (C) 2025 by NRCan
        email                : bryant.seth@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
#===============================================================================
# IMPORTS-------------
#===============================================================================


import os, sys, re
import sqlite3
import pandas as pd
import numpy as np

#PyQt
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import (
    QAction, QFileDialog, QListWidget, QTableWidgetItem, QDoubleSpinBox
    )

#qgis
from qgis.gui import QgsMapLayerComboBox
from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer, QgsMapLayerProxyModel, \
    QgsWkbTypes, QgsMapLayer, QgsLogger

 

from .hp.plug import (
    plugLogger, bind_layersListWidget, get_layer_info_from_combobox, bind_tableWidget
    )

from .parameters import (
    home_dir, plugin_dir, project_parameters_template_fp, project_db_schema_d,
    fileDialog_filter_str, hazDB_schema_d, hazDB_meta_template_fp
                         )

from .assertions import (
    assert_proj_db_fp, assert_proj_db, assert_haz_db, assert_haz_db_fp
    )

from .core import Model, _get_proj_meta_d
from .dialog_model import Model_config_dialog
#===============================================================================
# load UI and resources
#===============================================================================

#append the path (resources_rc workaround)
"""TODO: figure out if this is still needed or if there is a more elegant solution"""

resources_module_fp = os.path.join(plugin_dir, 'resources.py')
assert os.path.exists(resources_module_fp), resources_module_fp 
if not os.path.dirname(resources_module_fp) in sys.path:
    sys.path.append(os.path.dirname(resources_module_fp))

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
ui_fp = os.path.join(os.path.dirname(__file__), 'canflood2_dialog_main.ui')
assert os.path.exists(ui_fp), f'UI file not found: {ui_fp}'
FORM_CLASS, _ = uic.loadUiType(ui_fp, resource_suffix='') #Unknown C++ class: Qgis




#===============================================================================
# Dialog class
#===============================================================================
class Main_dialog_haz(object):
    """oragnizing hazard dialog functions here"""
    
    def _create_new_hazDB(self, fp, overwrite=True):
        """create a new hazard database file"""
        log = self.logger.getChild('_create_new_hazDB')
        
        #file check
        if os.path.exists(fp):
            log.warning(f'specified hazard database already exists overwrite={overwrite}')
            if overwrite:
                os.remove(fp)
            else:
                raise FileExistsError(f'specified hazard database already exists and overwrite is not set')
                
        
        log.debug(f'creating new hazard database at\n    {fp}')
        
        #=======================================================================
        # create the database tables
        #=======================================================================
        df_d = dict()
        table_name='04_haz_meta'
        df_d[table_name] = pd.read_csv(hazDB_meta_template_fp)
        
        
        table_name='05_haz_events'
        df_d[table_name] = hazDB_schema_d[table_name].copy()
        #===================================================================
        # build the database
        #===================================================================
        with sqlite3.connect(fp) as conn:
            #create the tables
            for table_name, df in df_d.items():
                df.to_sql(table_name, conn, if_exists='replace', index=False)
                
            #check the database
            assert_haz_db(conn)
            
        log.info(f'created new hazard database at\n    {fp}')
        
        self._save_haz_ui_to_hazDB(hazDB_fp=fp)
        
        return
        
    def _save_haz_ui_to_hazDB(self, *args, hazDB_fp=None, projDB_fp=None):
        """save the current UI state to the hazard database"""\
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('_save_haz_ui_to_hazDB')
        if hazDB_fp is None:
            hazDB_fp = self.lineEdit_HZ_hazDB_fp.text()
            
        if projDB_fp is None:
            projDB_fp = self.lineEdit_PS_projDB_fp.text()
            
        if hazDB_fp == '' or hazDB_fp is None:
            raise ValueError('no hazard database file path specified')
        
        assert_haz_db_fp(hazDB_fp)
        
        log.debug(f'saving UI to hazard database at\n    {hazDB_fp}')
        #=======================================================================
        # open and load
        #=======================================================================
        df_d=dict()
        with sqlite3.connect(hazDB_fp) as conn:
            
            #===================================================================
            # update hazard meta
            #===================================================================
            table_name='04_haz_meta'
            df_d[table_name] = pd.read_sql('SELECT * FROM [{}]'.format(table_name), conn)
            
            d = self._retrieve_ui_state_from_df_template(df_d[table_name])
            df_d[table_name]['value'] = pd.Series(d)
            
            #===================================================================
            # update the hazard events table
            #===================================================================
            table_name='05_haz_events'
            """always starting fresh"""
            df_d[table_name] = hazDB_schema_d[table_name].copy()
            
            #read the dataframe from the table widget
            eventMeta_df = self.tableWidget_HZ_eventMeta.get_df_from_QTableWidget()
            
            if len(eventMeta_df)>0:
                raise NotImplementedError('stopped here')
                #update the haz_events with the user entered event metadata
                pd.concat([df_d[table_name],eventMeta_df])
            
            #write the tables
            for k, df in df_d.items():
                assert k in hazDB_schema_d.keys(), k
                df.to_sql(k, conn, if_exists='replace', index=False)
                log.debug(f'    updated hazDB table \'{k}\' w/ {df.shape}')
                
            assert_haz_db(conn)
        log.debug(f'finished saving UI to hazard database at\n    {hazDB_fp}')
        #=======================================================================
        # update the project database as well
        #=======================================================================
        """mirroring the hazard tables inside the project database
            gives us a more portalbe project database
            makes accessing the full table stack easier
            
        users can still load a different hazard database, then load this into the project database
        """
        if not (projDB_fp is None or projDB_fp == ''):
            log.debug(f'updating project database w/ hazard tables \n    {projDB_fp}')
            with sqlite3.connect(projDB_fp) as conn:
                for k, df in df_d.items():
                    assert k in project_db_schema_d.keys(), k
                    df.to_sql(k, conn, if_exists='replace', index=False)
                    log.debug(f'    updated projDB table \'{k}\' w/ {df.shape}')
                    
                assert_proj_db(conn)
        else:
            log.warning(f'no project database found... hazard tables not mirrored')
        
        #close sqlite

        log.push(f'UI state saved to hazards database')
            
        return
            
            
            
            
            
            
            
        
 
        
 
    
class Main_dialog(Main_dialog_haz, QtWidgets.QDialog, FORM_CLASS):
    
 
    
    def __init__(self, parent=None,iface=None,debug_logger=None):
        """dialog for main CanFlood window
        
        
        Parameters
        ----------
        parent : QWidget
            parent widget
        iface : QgsInterface
            QGIS interface
            
        debug_logger : logging.Logger
            logger pytests
        """
        #not sure why the template passes parent here
        #super(Main_dialog, self).__init__(parent)
        super(Main_dialog, self).__init__()
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.parent=parent
        self.iface=iface 
        
        self.model_index_d = dict() #for tracking the model instances
        #{category_code:{modelid:Model}}
        
        #setup logger
        self.logger = plugLogger(
            self.iface, parent=self, statusQlab=self.progressText,debug_logger=debug_logger,
            log_nm='MD',
            )
        
        self.connect_slots()
        
        self.logger.debug('Main_dialog initialized')
        
    def connect_slots(self):
        """on launch of ui, populate and connect"""
 
        log = self.logger.getChild('connect_slots')
        log.debug('connecting slots')
        
        #=======================================================================
        # general----------------
        #=======================================================================
        
        
        def close_dialog():
            self.logger.push(f'dialog reset')
            if not self.parent is None:
                self.parent.dlg=None
                self.parent.first_start=True #not ideal
            self.close()
        
        self.pushButton_close.clicked.connect(close_dialog)
        
        
        self.pushButton_save.clicked.connect(self._save_ui_to_projDB)
        
        
        """not using 
        self.cancel_pushButton.clicked.connect(self.action_cancel_process)"""
        
        from canflood2 import __version__
        self.label_version.setText(f'v{__version__}')
        
        #=======================================================================
        # Project Setup tab-----------
        #=======================================================================
        
        #=======================================================================
        # project database file
        #=======================================================================
        
        def _new_projDB():
            """wrapper for the New Project Database button"""
 
            
            filename = None
            try:
                filename, _ = QFileDialog.getSaveFileName(
                    self,  # Parent widget (your dialog)
                    "Save project database (sqlite) file",  # Dialog title
                    home_dir,  # Initial directory (optional, use current working dir by default)
                    fileDialog_filter_str
                )
            except Exception as e:
                log.warning(f'error on file dialog: {e}')
                
            if filename:
                self.lineEdit_PS_projDB_fp.setText(filename)
                self._create_new_projDB(filename)
                self.pushButton_save.setEnabled(True)
                log.push(f'created new project database at\n    {filename}')
                
        self.pushButton_PS_projDB_new.clicked.connect(_new_projDB)
            
            
            
        def load_project_database_ui():
            log.debug('create_new_project_database_ui')
            print('create_new_project_database_ui')
            filename, _ = QFileDialog.getOpenFileName(
                self,  # Parent widget (your dialog)
                "Open project database (sqlite) file",  # Dialog title
                home_dir,  # Initial directory (optional, use current working dir by default)
                fileDialog_filter_str  # Example file filters
                )
            if filename:
                self.lineEdit_PS_projDB_fp.setText(filename) 
                self._load_project_database()
                
                #activate the save button
                self.pushButton_save.setEnabled(True)            
 
        self.pushButton_PS_projDB_load.clicked.connect(load_project_database_ui)
        

                
        
        
        #=======================================================================
        # Study Area Polygon
        #=======================================================================
        self.comboBox_aoi.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.comboBox_aoi.setCurrentIndex(-1)
        
        
        #=======================================================================
        # DEM Raster
        #=======================================================================
        self.comboBox_dem.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.comboBox_dem.setCurrentIndex(-1)
        
        #=======================================================================
        # Hazard scenario tab------------
        #=======================================================================
        
        #=======================================================================
        # Hazard Scenario Database File
        #=======================================================================
        def create_new_hazard_database_ui():
            filename, _ = QFileDialog.getSaveFileName(
                self,  # Parent widget (your dialog)
                "Save hazard database (sqlite) file",  # Dialog title
                home_dir,  # Initial directory (optional, use current working dir by default)
                "sqlite database files (*.db)"  # Example file filters
                )
            if filename:
                self.lineEdit_HZ_hazDB_fp.setText(filename)
                self._create_new_hazDB(filename)
                
        self.pushButton_HZ_hazDB_new.clicked.connect(create_new_hazard_database_ui)
        
        
        def load_hazard_database_ui():
            filename, _ = QFileDialog.getOpenFileName(
                self,  # Parent widget (your dialog)
                "Open hazard database (sqlite) file",  # Dialog title
                home_dir,  # Initial directory (optional, use current working dir by default)
                "sqlite database files (*.db)"  # Example file filters
                )
            if filename:
                self.lineEdit_HZ_hazDB_fp.setText(filename)
                
        self.pushButton_HZ_hazDB_load.clicked.connect(load_hazard_database_ui)
        

        
        
        
        #=======================================================================
        # #Hazard Event Rasters
        #=======================================================================
        #setup the list widget and add some special methods
        lv = self.listView_HZ_hrlay 
        bind_layersListWidget(lv, log, iface=self.iface,layerType=QgsMapLayer.RasterLayer)
        
        #connect standard hazars selection buttons
        self.pushButton_HZ_hrlay_selectAll.clicked.connect(lv.check_all)
        self.pushButton_HZ_hrlay_selectVis.clicked.connect(lv.select_visible)
        self.pushButton_HZ_hrlay_canvas.clicked.connect(lv.select_canvas)
        self.pushButton_HZ_hrlay_clear.clicked.connect(lv.clear_checks)
        self.pushButton_HZ_refresh.clicked.connect(lambda x: lv.populate_layers())
        
        #TODO: add a button to select all layers matching some string (e.g., 'haz')
        
        lv.populate_layers() #do an intial popluation.
        
        #connect loading into the event metadata view
        def load_selected_rasters_to_event_metadata():
 
            #retrieve the selected layers from teh above table
            layers = self.listView_HZ_hrlay.get_selected_layers()
            
            w = self.tableWidget_HZ_eventMeta
            
            # Clear any existing contents and rows.
            w.clearContents()
            w.setRowCount(len(layers))
        
            # Set up the table with 3 columns and appropriate header labels.
            w.setColumnCount(3)
            w.setHorizontalHeaderLabels(["Event Name", "Probability", "Metadata (optional)"])
        
            # Loop through the layers list and create a new row for each.
            for rindx, ename in enumerate(layers):
                w.setItem(rindx, 0, QTableWidgetItem(ename)) 
                
                # Create a QDoubleSpinBox for the Probability column
                probability_spinbox = QDoubleSpinBox()
                probability_spinbox.setRange(0.0, 9999)  # Set range for probability values
                probability_spinbox.setDecimals(4)  # Set the number of decimal places
                w.setCellWidget(rindx, 1, probability_spinbox)
                
            # Set the third column to expand to the remaining space
            header = w.horizontalHeader()
            header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        
        self.pushButton_HZ_hrlay_load.clicked.connect(load_selected_rasters_to_event_metadata)
        
        #bind some methods to the tableWidget_HZ_eventMeta
        bind_tableWidget(self.tableWidget_HZ_eventMeta, self.logger, iface=self.iface)
        
        #=======================================================================
        # Model Suite---------
        #=======================================================================
        self.Model_config_dialog = Model_config_dialog(self.iface, parent=self, logger=self.logger)
        
        #populate a model instance into each of the 7 categories, using 'horizontalLayout_MS_modelTemplate' as a template
 
        
        #retrieve all the group boxes inside the model set:
        modelSet_groupBoxes = self.groupBox_MS_modelSet.findChildren(QtWidgets.QGroupBox)
        
        # Loop through each group box, and load the model template into it.
        for gb in modelSet_groupBoxes:
            #groupbox_name = gb.objectName()
            groupbox_title = gb.title()
            
            category_code, category_desc = extract_gropubox_codes(groupbox_title)
            
            
            # Create a new layout for the group box if it doesn't have one
            if gb.layout() is None:
                gb.setLayout(QtWidgets.QVBoxLayout())
        
            # Add the loaded widget to the group box's layout
            self.add_model(gb.layout(), category_code, category_desc)
 
            
        """stopped here... need to dynamically rename things ad collect in a contaoiner
        to access later"""
            

            
            
        log.debug("populated model suite")
        """
        self.show()
        """
        
        
        #=======================================================================
        # wrap
        #=======================================================================
        log.debug('slots connected')
        
    def add_model(self, layout, category_code, category_desc=None, logger=None):
        """start a model object, then add the template to the layout"""
        if logger is None: logger=self.logger.getChild('add_model')
        
        #setup the UI        
        widget = load_model_widget_template() #load the model template
        layout.addWidget(widget) #add it to the widget
        
        #retrieve the modelid
        if not category_code in self.model_index_d:
            self.model_index_d[category_code] = dict()
            
        modelid = len(self.model_index_d[category_code])
        
        
        #setup the model object
        wrkr = Model(parent=self,
                     widget_suite=widget, 
                     category_code=category_code, category_desc=category_desc, modelid=modelid,
                     logger=self.logger)
        
        #connect the buttons
        widget.pushButton_mod_run.clicked.connect(wrkr.run_model)
        widget.pushButton_mod_config.clicked.connect(wrkr.launch_config_ui)
 
 
        
        #add to the index
        assert not modelid in self.model_index_d[category_code]
        self.model_index_d[category_code][modelid] = wrkr
        
    def _clear_all_models(self):
        """clear all the models"""

        log = self.logger.getChild('_clear_all_models')
        cnt=0
        log.debug('clearing all models')
        for category_code, modelid_d in self.model_index_d.items():
            for modelid, wrkr in modelid_d.items():
                wrkr.__exit__()
                del wrkr
                
        self.model_index_d = dict()
        log.info(f'cleared {cnt} models')
        
        

    
    def _create_new_projDB(self, fp, overwrite=True):
        """create a new project database file"""
        log = self.logger.getChild('_create_new_projDB')
        
        #file check
        if os.path.exists(fp):
            if overwrite:
                log.warning(f'specified project database already exists and will be overwritten')
                os.remove(fp)
            else:
                raise FileExistsError(f'specified project database already exists and overwrite is not set')
            
        df_d = dict()
        #=======================================================================
        # #build the project metadata
        #=======================================================================
        table_name='01_project_meta'
        d = _get_proj_meta_d(log)
        d.update(dict(function_name='_create_new_projDB', misc=''))
        df_d[table_name] = pd.DataFrame(d)
        
        """
        table
        tabel
        """
        #=======================================================================
        # #build the project parameters
        #=======================================================================
        table_name='02_project_parameters'
        df_d[table_name] = pd.read_csv(project_parameters_template_fp)
        
        #check the widget names match
        for widgetName in df_d[table_name]['widgetName']:
            assert hasattr(self, widgetName), f'widgetName not found: {widgetName}'
        
        
        #=======================================================================
        # model suite template
        #=======================================================================
        """this will be over-written in _save_ui_to_projDB
        but we need it here to pass the check
        """
        table_name='03_model_suite_index'
        df_d[table_name] = project_db_schema_d[table_name].copy()
        
        #=======================================================================
        # hazard tables
        #=======================================================================
        #hazard meta
        table_name='04_haz_meta'
        df_d[table_name] = pd.read_csv(hazDB_meta_template_fp)
        
        #others
        for k, v in hazDB_schema_d.items():
            if not k==table_name:
                assert isinstance(v, pd.DataFrame), k
                df_d[k] = v.copy()
        
        #=======================================================================
        # #build/write to the database
        #=======================================================================
        log.debug(f'init project SQLite db at\n    {fp}')
        with sqlite3.connect(fp) as conn:
            for k, df in df_d.items():
                assert k in project_db_schema_d.keys(), k
                df.to_sql(k, conn, if_exists='replace', index=False)
                
            assert_proj_db(conn)
                
        log.info(f'created new project database w/ {len(df_d)} tables at\n    {fp}')
        
        #=======================================================================
        # wrap
        #=======================================================================
        self._save_ui_to_projDB(projDB_fp=fp)
        
        

    def _retrieve_ui_state_from_df_template(self, df):
        """take a dataframe with widget name columns and return a dictionary of widget values
        
        Parameters
        ----------
        df : pd.DataFrame
            columns: 'widgetName'
        """
        d = dict()
        for i, row in df.iterrows():
 
            widgetName = row['widgetName']
            #get the widget
            if not hasattr(self, widgetName):
                raise AttributeError(f'widgetName not found: {widgetName}')
            
            widget = getattr(self, widgetName)
            #retrieve value from widget
            if isinstance(widget, QtWidgets.QLineEdit):
                v = widget.text()
            elif isinstance(widget, QgsMapLayerComboBox):
                _, v = get_layer_info_from_combobox(widget)
            elif isinstance(widget, QtWidgets.QComboBox):
                v = widget.currentText()
            elif isinstance(widget, QtWidgets.QRadioButton):
                v = widget.isChecked()                
            else:
                raise NotImplementedError(f'widget type not implemented: {widget}')
            if (not v is None) and (v != ''):
                d[i] = v
            else:
                d[i] = np.nan
                
        #check the indicides match
 
        if not df.index.equals(pd.Series(d).index):
            raise ValueError("Indexes do not match")
        

        return d

    def _save_ui_to_projDB(self, *args, projDB_fp=None):
        """save the current UI state to the project database"""
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('_save_ui_to_projDB')
        if projDB_fp is None:
            projDB_fp = self.lineEdit_PS_projDB_fp.text()
        
        if projDB_fp == '' or projDB_fp is None:
            raise ValueError('no project database file path specified')
        
        assert_proj_db_fp(projDB_fp)
        log.debug(f'saving UI to project database at\n    {projDB_fp}')
        #=======================================================================
        # open and load
        #=======================================================================
        df_d=dict()
        with sqlite3.connect(projDB_fp) as conn:

            
            #===================================================================
            # update project metadata
            #===================================================================
            table_name='01_project_meta'
            d = _get_proj_meta_d(log)
            d.update(dict(function_name='_save_ui_to_projDB', misc=''))
            df_d[table_name] = pd.DataFrame(d)
            
            #===================================================================
            # #update the project parameters
            #===================================================================
            table_name='02_project_parameters'
            df_d[table_name] = pd.read_sql('SELECT * FROM [{}]'.format(table_name), conn)
            
            d = self._retrieve_ui_state_from_df_template(df_d[table_name])
            

            
            df_d[table_name]['value'] = pd.Series(d)
 
            
            
            #===================================================================
            # update the model suite index
            #===================================================================
            table_name='03_model_suite_index'
            """no... always just start a new one
            df_d[table_name] = pd.read_sql('SELECT * FROM [{}]'.format(table_name), conn)
            """
            blank_df = project_db_schema_d[table_name].copy()
 
            d=dict()
 
        
            for category_code, modelid_d in self.model_index_d.items():
 
                for modelid, wrkr in modelid_d.items():
                    #add the model
                    d[f'{category_code}_{modelid}'] = wrkr.get_index_d()
            
            # Convert the dictionary to a DataFrame and concatenate with the blank DataFrame
            result_df = pd.concat([blank_df, pd.DataFrame(d).T], ignore_index=True)
            
            # Reindex the result DataFrame to match the blank DataFrame's columns
            df_d[table_name] = result_df.reindex(columns=blank_df.columns).astype(blank_df.dtypes.to_dict())
            
 
 
            
            #===================================================================
            # write all the tables
            #===================================================================
            for k, df in df_d.items():
                assert k in project_db_schema_d.keys(), k
                df.to_sql(k, conn, if_exists='replace', index=False)
                log.debug(f'updated table \'{k}\' w/ {df.shape}')
                
        #close sqlite
        log.debug(f'updated {len(df_d)} tables in project database at\n    {projDB_fp}')
        log.push(f'UI state saved to project database')
            
        return
        
    def _projDB_get_tables(self, *table_names, projDB_fp=None):
        """Convenience wrapper to get multiple tables as DataFrames.
    
        Parameters:
        *table_names: Variable number of table names (str) to fetch.
        projDB_fp: Optional; path to the project database file. If None, it will use the value from self.lineEdit_PS_projDB_fp.text().
    
        Returns:
        If a single table name is passed, returns a DataFrame; otherwise, returns a tuple of DataFrames in the same order as table_names.
        """
        if projDB_fp is None:
            projDB_fp = self.lineEdit_PS_projDB_fp.text()
    
        assert_proj_db_fp(projDB_fp)
    
        with sqlite3.connect(projDB_fp) as conn:
            dfs = tuple(pd.read_sql(f'SELECT * FROM [{name}]', conn) for name in table_names)
    
        return dfs[0] if len(dfs) == 1 else dfs
        
            
 
        
    def _load_project_database(self):
        """load an existing project database file"""
        raise NotImplementedError('stopped here')
        fp =  self.lineEdit_PS_projDB_fp.text()
 
        #=======================================================================
        # load data tables
        #=======================================================================
        with sqlite3.connect(fp) as conn:
            assert_proj_db(conn)
 
 
            
            #=======================================================================
            # set the ui state from the project parameters
            #=======================================================================
            table_name='02_project_parameters'
            df = pd.read_sql('SELECT * FROM [{}]'.format(table_name), conn)
            
            for k, row in df.iterrows():
                widgetName = row['widgetName']
                value = row['value']
                
                #get the widget
                widget = getattr(self, widgetName)
                
                #set the value
                if isinstance(widget, QtWidgets.QLineEdit):
                    widget.setText(value)
                elif isinstance(widget, QtWidgets.QComboBox):
                    widget.setCurrentText(value)
                else:
                    raise NotImplementedError(f'widget type not implemented: {widget}')
                
            #=======================================================================
            # set the model suite
            #=======================================================================
            table_name='03_model_suite_index'
            df = pd.read_sql('SELECT * FROM [{}]'.format(table_name), conn)
            #clear the model suite
            self._clear_all_models()
            
            raise NotImplementedError('stopped here')
            for k, row in model_suite_index_df.iterrows():
                category_code = row['category_code']
                modelid = row['modelid']
                model_parameter_table_name = row['model_parameter_table_name']
                
                #get this group box
                
                
                #add the model                        
                wrkr = self.add_model()
                
                #load the model from teh table
                #load the table
                wrkr.load_from_table()
                

            
            

            
        
            
        
        
        
        
        
        
#===============================================================================
# helpers-----
#===============================================================================
# Load the widget from the .ui file
def load_model_widget_template(
    model_template_ui = os.path.join(os.path.dirname(__file__), 'canflood2_model_widget.ui'), 
    parent=None):
    """load the model widget template"""
    assert os.path.exists(model_template_ui), f'bad model_template_ui: {model_template_ui}'
    widget = QtWidgets.QWidget(parent)
    uic.loadUi(model_template_ui, widget)
    return widget

# Path to the model template UI file
def extract_gropubox_codes(input_string):
    """
    Extracts 'c1' and the remaining text from the input string.

    Parameters:
    input_string (str): The input string in the format '[c1] remaining text'.

    Returns:
    tuple: A tuple containing 'c1' and the remaining text.
    """
    pattern = r'\[(.*?)\]\s*(.*)'
    match = re.match(pattern, input_string)

    if match:
        c1 = match.group(1)
        remaining_text = match.group(2)
        return c1, remaining_text
    else:
        return None, None
        
