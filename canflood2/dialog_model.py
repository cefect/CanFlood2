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


from PyQt5 import uic, QtWidgets
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
        
        
    def _load_model(self, model):
        """load the model worker into the dialog"""
        log = self.logger.getChild('load_model')
        
        #set the lables
        self.label_mod_modelid.setText('%2d'%model.modelid)
        self.label_mod_asset.setText(model.asset_label)
        self.label_mod_consq.setText(model.consq_label)
        self.label_mod_status.setText(model.status_label)
        
        self.label_category.setText(f'[{model.category_code}] {model.category_desc}')
        
        
        log.debug(f'loaded model {model.name}')
        
        
    def _save_and_close(self):
        """save and close the dialog"""
        log = self.logger.getChild('_save_and_close')
        log.debug('closing')
        
        self.accept()
        
    def _close(self):
        """close the dialog"""
 
        
        self.reject()