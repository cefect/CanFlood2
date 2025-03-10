'''
Created on Mar 6, 2025

@author: cef
ui dialog class for model config window
'''

#==============================================================================
# imports-----------
#==============================================================================
#python
import sys, os, datetime, time, configparser
import pandas as pd


from PyQt5 import uic, QtWidgets

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRasterLayer, QgsMapLayerProxyModel,
    QgsWkbTypes, QgsMapLayer, QgsLogger,
    )

from .hp.basic import view_web_df as view
from .hp.qt import set_widget_value, get_widget_value

from .parameters import consequence_category_d



from  .core import Model
#===============================================================================
# load UI file
#===============================================================================
# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
ui_fp = os.path.join(os.path.dirname(__file__), 'canflood2_model_config.ui')
assert os.path.exists(ui_fp), 'failed to find the ui file: \n    %s'%ui_fp
FORM_CLASS, _ = uic.loadUiType(ui_fp)


class Model_config_dialog(QtWidgets.QDialog, FORM_CLASS, Model):
    
    def __init__(self, 
                 iface, 
                 parent=None,
                 logger=None,

                 ):
        """called on stawrtup"""
        super(Model_config_dialog, self).__init__(parent) #only calls QtWidgets.QDialog
        
 
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
        # generic
        #=======================================================================
        self.pushButton_ok.clicked.connect(self._save_and_close)
        self.pushButton_close.clicked.connect(self._close)
        self.pushButton_run.clicked.connect(self._run_model)
        
        #=======================================================================
        # Asset Inventory
        #=======================================================================
        self.comboBox_finv_vlay.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.comboBox_finv_vlay.setCurrentIndex(-1)
        
        
        
        log.debug('slots connected')
        
        
    def load_model(self, model, projDB_fp=None):
        """load the model worker into the dialog"""
        log = self.logger.getChild('load_model')
        
        self.model = model
        if projDB_fp is None:
            projDB_fp = self.parent.get_projDB_fp()
        #=======================================================================
        # #load parameters from the table
        #=======================================================================
        params_df = model.get_model_tables('table_parameters', projDB_fp=projDB_fp)
        
        #get just those with values
        params_df = params_df.loc[:, ['widgetName', 'value', 'value2']].dropna(subset=['value', 'widgetName']
                                       ).set_index('widgetName')
 
        if len(params_df)==0:
            log.debug(f'loaded {len(params_df)} parameters for model {model.name}')
            for k,row in params_df.iterrows():
                widget = getattr(self, k)
                
                #simple
                if pd.isnull(row['value2']):
                    set_widget_value(widget, row['value'])
                    
                #layers
                else:
                    raise NotImplementedError(f'need to set the mapbox widget based on the layer id')
                
        else:
            log.debug(f'paramter table empty for model {model.name}')
            
            
            
        
        
        #=======================================================================
        # #set the lables
        #=======================================================================
        self.label_mod_modelid.setText('%2d'%model.modelid)
        self.label_mod_asset.setText(model.asset_label)
        self.label_mod_consq.setText(model.consq_label)
        self.label_mod_status.setText(model.status_label)        
        self.label_category.setText(consequence_category_d[model.category_code])
        
        
        log.debug(f'loaded model {model.name}')
        
    def _run_model(self):
        self.model.run_model()
        
        
    def _save_and_close(self):
        """write the model config window parameter state to the approriate table_parameters
        this is not a full run, just how the user would expect to close/open the dialog 
        and see the parameters for the specific model"""
        log = self.logger.getChild('_save_and_close')
        log.debug('closing')
        
        model = self.model
        
        #=======================================================================
        # retrieve, set, and save the paramter table
        #=======================================================================
        #retrieve the parameter table
        params_df = model.get_model_tables('table_parameters')
        
        #loop through each widget and collect the state from the ui
        d = dict()
        for i, widgetName in params_df['widgetName'].dropna().items():
            widget = getattr(self, widgetName)
            d[i] = get_widget_value(widget)
 
        s = pd.Series({k:v for k,v in d.items() if not v==''}, name='value')
        
        #update the parameters table with the ui state
        params_df.loc[s.index, 'value'] = s
        
        #write to the parent
        model.set_model_tables({'table_parameters': params_df}, logger=log)
 
        log.debug(f'saved {len(s)} parameters for model {model.name}')
        
        self.accept()
        
    def _close(self):
        """close the dialog"""
 
        
        self.reject()
        

