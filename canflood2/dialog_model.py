'''
Created on Mar 6, 2025

@author: cef
ui dialog class for model config window
'''

#==============================================================================
# imports-----------
#==============================================================================
#python
import sys, os, datetime, time, configparser, logging, sqlite3
import pandas as pd


from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import (
    QAction, QFileDialog, QListWidget, QTableWidgetItem, QDoubleSpinBox,
    QLabel, QPushButton, QProgressBar
    )

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRasterLayer, QgsMapLayerProxyModel,
    QgsWkbTypes, QgsMapLayer, QgsLogger,
    )

from .hp.basic import view_web_df as view
from .hp.qt import set_widget_value, get_widget_value
from .hp.plug import bind_QgsFieldComboBox

from .assertions import assert_projDB_fp, assert_vfunc_fp, assert_projDB_conn

from .parameters import consequence_category_d, home_dir, project_db_schema_d
from .hp.vfunc import  load_vfunc_to_df_d, vfunc_df_to_dict, vfunc_cdf_chk_d, vfunc_df_to_meta_and_ddf

from .core import Model




#===============================================================================
# load UI file
#===============================================================================
# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
ui_fp = os.path.join(os.path.dirname(__file__), 'canflood2_model_config.ui')
assert os.path.exists(ui_fp), 'failed to find the ui file: \n    %s'%ui_fp
FORM_CLASS, _ = uic.loadUiType(ui_fp)



class Model_config_dialog(QtWidgets.QDialog, FORM_CLASS):
    
    
    
    def __init__(self, 
                 iface, 
                 parent=None,
                 logger=None,

                 ):
        """called on stawrtup"""
        super(Model_config_dialog, self).__init__(parent) #only calls QtWidgets.QDialog
        
 
        self.parent=parent
        self.iface = iface
        self.logger=logger.getChild('model_config')
        self.setupUi(self)
        
        self.connect_slots()
        
        self.logger.debug('Model_config_dialog initialized')
        
    def connect_slots(self):
        """on launch of ui, populate and connect"""
 
        log = self.logger.getChild('connect_slots')
        log.debug('connecting slots')
 
        #=======================================================================
        # generic-------
        #=======================================================================
        self.pushButton_ok.clicked.connect(self._save_and_close)
        self.pushButton_close.clicked.connect(self._close)
        self.pushButton_run.clicked.connect(self._run_model)
        
        #=======================================================================
        # Asset Inventory--------
        #=======================================================================
        self.comboBox_finv_vlay.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.comboBox_finv_vlay.setCurrentIndex(-1)
        
        #bind the exposure geometry label
        def update_finv_geometry_label():
            layer = self.comboBox_finv_vlay.currentLayer()
            if not layer is None:
                self.label_EX_geometryType.setText(QgsWkbTypes.displayString(layer.wkbType()))
            
        self.comboBox_finv_vlay.layerChanged.connect(update_finv_geometry_label)
        
        #=======================================================================
        # #finv bindings
        #=======================================================================
        #loop through and connect all the field combo boxes to the finv map layer combo box
        for comboBox, fn_str in {
            self.mFieldComboBox_cid:'xid',
            self.mFieldComboBox_AI_01_scale:'f0_scale',
            self.mFieldComboBox_AI_01_tag:'f0_tag',
            self.mFieldComboBox_AI_01_elev:'f0_elev',
            self.mFieldComboBox_AI_01_cap:'f0_cap',
            }.items():
            
            bind_QgsFieldComboBox(comboBox, 
                                  signal_emmiter_widget=self.comboBox_finv_vlay,
                                  fn_str=fn_str)
        
        
        #=======================================================================
        # Vulnerability-----------
        #=======================================================================
        def load_vfunc_fp():
            filename, _ = QFileDialog.getOpenFileName(
                self,  # Parent widget (your dialog)
                "Select Vulnerability Function Set",  # Dialog title
                home_dir,  # Initial directory (optional, use current working dir by default)
                "Excel Files (*.xls *.xlsx)",
                )
            if filename:
                self._vfunc_load_from_file(filename)

                
             
        self.pushButton_V_vfunc_load.clicked.connect(load_vfunc_fp)
        

        
        
        log.debug('slots connected')
        
 
        
    def _vfunc_load_from_file(self, vfunc_fp, logger=None, projDB_fp=None):
        """load the vfunc, do some checks, and set some stats
        
        builds 
            06_vfunc_index
            07_vfunc_data
        
        
        User needs to manually import
        
        only the finv contains a model-specific reference to the vfuncs
            in general, vfuncs are shared across the project
        """
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('_vfunc_load_from_file')
        
        if projDB_fp is None:
            projDB_fp = self.parent.get_projDB_fp()
 
        assert_vfunc_fp(vfunc_fp)
        
        log.info(f'loading vfunc from {vfunc_fp}')
        #=======================================================================
        # get stats
        #=======================================================================
        df_d = load_vfunc_to_df_d(vfunc_fp)      
        
        #set count
        self.label_V_functionCount.setText(str(len(df_d)))
        
        log.debug(f'loaded {len(df_d)} vfuncs from {vfunc_fp}')
        #=======================================================================
        # build index and data table
        #=======================================================================
        #look through each and collect some info
        index_d = dict()
        data_d = dict()
        for k, df in df_d.items():
            #cv_d = vfunc_df_to_dict(df)
            meta_d, ddf = vfunc_df_to_meta_and_ddf(df)
            assert k==meta_d['tag'], 'mismatch on tag on %s'%k
            
            #filter indexers
            """just keep everything
            NO... might get some non-conforming new vfunc sets
            better to just use those from the check dict
            """ 
            index_d[k] = {k:v for k,v in meta_d.items() if k in vfunc_cdf_chk_d.keys()}
            #index_d[k] = meta_d
            
            #collect df-d table
            data_d[k] = ddf
            
        vfunc_index_df = pd.DataFrame.from_dict(index_d, orient='index').reset_index(drop=True)
        vfunc_data_dx = pd.concat(data_d, names=['tag', 'exposure']) 
 
        
        """
        view(index_df)
        """
        
        #create table names
        """NO... using a single data table now
 
        index_df['table_name'] =  'vfunc_' + index_df['tag'].str.replace('_', '')"""        
        
        log.debug(f'built vfunc index w/ {len(vfunc_index_df)} records')
        
 
        #=======================================================================
        # filter based on finv
        #=======================================================================
        """ignoring this for now
        if 'table_finv' in model.get_table_names_all():
            raise NotImplementedError('remove vfuncs not in the finv')
        """
        
        #=======================================================================
        # update projDB
        #=======================================================================
        with sqlite3.connect(projDB_fp) as conn:
            assert_projDB_conn(conn)
            
            set_df = lambda df, table_name: self.parent.projDB_set_tables({table_name:df}, logger=log, conn=conn)
            #===================================================================
            # # index
            #===================================================================
            table_name = '06_vfunc_index'
            df_old = pd.read_sql(f'SELECT * FROM [{table_name}]', conn)
            
            if len(df_old)==0:
                df = vfunc_index_df
            else:
                raise NotImplementedError(f'need to merge the new vfunc index with the old')
            
            set_df(df, table_name)
 
            #===================================================================
            # data
            #===================================================================
            
            table_name='07_vfunc_data'
            df_old = pd.read_sql(f'SELECT * FROM [{table_name}]', conn)
            
            if len(df_old)==0:
                df = vfunc_data_dx.reset_index()
            else:
                raise NotImplementedError(f'need to merge the new vfunc data with the old')
            
            set_df(df, table_name)
    
 
            #final consistency check
            assert_projDB_conn(conn, check_consistency=True)
 
        
        #=======================================================================
        # wrap
        #=======================================================================
        log.info(f'finished loading vfuncs from {os.path.basename(vfunc_fp)}')

        
    def load_model(self, model, projDB_fp=None):
        """load the model worker into the dialog"""
        log = self.logger.getChild('load_model')
        assert isinstance(model, Model), f'bad model type: {type(model)}'
        self.model = model
        if projDB_fp is None:
            projDB_fp = self.parent.get_projDB_fp()
            
        log.debug(f'loading model {model.name} onto configDialog')
        #=======================================================================
        # #load parameters from the table
        #=======================================================================
        params_df = model.get_table_parameters(projDB_fp=projDB_fp)
        
        #get just those with values
        params_df = params_df.loc[:, ['widgetName', 'value']].dropna(subset=['value', 'widgetName']
                                       ).set_index('widgetName')
 
        if len(params_df)==0:
            log.debug(f'loaded {len(params_df)} parameters for model {model.name}')
            for k,row in params_df.iterrows():
                widget = getattr(self, k)
                set_widget_value(widget, row['value'])
 
                
        else:
            log.debug(f'paramter table empty for model {model.name}')
            
            
            
        
        #=======================================================================
        # update hte labels
        #=======================================================================
        model.compute_status()
        self._update_model_labels(model=model)
 
        
        
        log.debug(f'finished loaded model {model.name}')
        
        assert not self.model is None, 'failed to load model'
        
    def _update_model_labels(self, model=None):
        """set the labels for the model"""
        log = self.logger.getChild('_update_model_labels')
        if model is None: model = self.model
        
        #retrieve from model
        s = model.get_model_index_ser().fillna('')
        
        self.label_mod_modelid.setText('%2d'%model.modelid)
        self.label_mod_asset.setText(s['asset_label'])
        self.label_mod_consq.setText(s['consq_label'])
        self.label_mod_status.setText(s['status'])        
        self.label_category.setText(consequence_category_d[s['category_code']]['desc'])
        
        log.debug(f'updated labels for model {model.name}')
        

        
        
        
        

    def _set_ui_to_table_parameters(self, model, logger=None):
        """write the model config window parameter state to the approriate table_parameters
        """
        if logger is None: logger = self.logger
        log = logger.getChild('_set_ui_to_table_parameters')
        
        #retrieve the parameter table
        params_df = model.get_tables('table_parameters').set_index('varName')
        
        """
        view(params_df)
        """
        #=======================================================================
        # collect from ui
        #=======================================================================
        #loop through each widget and collect the state from the ui
        d = dict()
        for i, widgetName in params_df['widgetName'].dropna().items():
            
            widget = getattr(self, widgetName)
            d[i] = get_widget_value(widget)
            
        #=======================================================================
        # specials
        #=======================================================================
        """maybe not the most elegent to add this here... but this attribute is special"""
        for k in ['status']:
            assert k in params_df.index
            d[k] = getattr(model, k)
        
 
        
        #=======================================================================
        # wrap
        #=======================================================================
        
        s = pd.Series(d, name='value').replace('', pd.NA)
        
        #update the parameters table with the ui state
        params_df.loc[s.index, 'value'] = s
        
        #write to the parent
        model.set_tables({'table_parameters':params_df.reset_index()}, logger=log)
        
        #=======================================================================
        # update model index
        #=======================================================================
        """called by set_tables()
        self.parent.update_model_index_dx(model, logger=log)"""
        
        log.push(f'saved {len(s)} parameters for model {model.name}')
        
    def _run_model(self):
        """run the model
        
    
        """
        
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('_run_model')
        model = self.model        
        assert not model is None, 'no model loaded'
        
 
        
        log.info(f'running model {model.name}')
        
        #=======================================================================
        # trigger save        
        #=======================================================================
        self._set_ui_to_table_parameters(model, logger=log)
        
        #=======================================================================
        # run it
        #=======================================================================
        model.run_model(projDB_fp=self.parent.get_projDB_fp())

    def _save_and_close(self):
        """save the dialog to the model parameters table"""
 
        log = self.logger.getChild('_save_and_close')
        log.debug('closing')
        
        model = self.model
        
        #=======================================================================
        # retrieve, set, and save the paramter table
        #=======================================================================
        self.model.compute_status()
        
        self._set_ui_to_table_parameters(model, logger=log)
        
 
 
        self._custom_cleanup()
        log.info(f'finished saving model {model.name}')
        self.accept()
        
    def _close(self):
        """close the dialog without saving"""
 
        self._custom_cleanup()
        self.reject()
        
    def _custom_cleanup(self):
        
        self.parent._update_model_widget_labels(model=self.model)
        
        self.model=None
        
        
        
        
        
        
        
        
        
        
        
        
        

