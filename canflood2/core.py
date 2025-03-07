'''
Created on Mar 6, 2025

@author: cef
'''
import os, sys, platform
import pandas as pd
from datetime import datetime

from PyQt5.QtWidgets import QLabel, QPushButton, QProgressBar

from . import __version__

class Model(object):
    """Model class for CANFlood2
    
    configured via the 'Model Suite' tab in the main dialog.
        see .add_model()
        
        
    model states
        incomplete – Implies the template is still in an unfinished, configurable state.
        Ready – Indicates that the model is configured and waiting to run.
        Failed – Clearly denotes that a model run has encountered an error.
        Complete – Conveys that the model run has finished successfully.
    """
    
    # Widget attributes as a dictionary: {objectName: widget type}
    widget_d = {
        'label_mod_modelid': QLabel,
        'label_mod_asset': QLabel,
        'label_mod_consq': QLabel,
        'label_mod_status': QLabel,
        'progressBar_mod': QProgressBar,
        'pushButton_mod_run': QPushButton,
        'pushButton_mod_config': QPushButton,
        'pushButton_mod_plus': QPushButton,
        'pushButton_mod_minus': QPushButton
    }
    
    def __init__(self,
                 parent=None, 
                 widget_suite=None,
                  
                 category_code='c1', category_desc='desc',
                 modelid=0, logger=None,
                 asset_label='', consq_label='',status_label='incomplete'
                 ):
        """Constructor for the model class.
        
        Parameters
        ----------
        widget_suite : Qwidget_suite
            The template widget_suite with all the ui
        asset_label: str
            main asset label for displaying on teh widget_suite
            useful if we are copying a model
            
        consq_label: str
            main consequence label for displaying on teh widget_suite
 
            
        """
            
            
        self.parent=parent
        self.category_code=category_code
        self.category_desc=category_desc
        self.modelid=modelid
        self.asset_label=asset_label
        self.consq_label=consq_label
        self.status_label=status_label
        self.name = f'{category_code}_{modelid}'
        self.logger = logger.getChild(self.name)
        
        if not widget_suite is None:
            self._attach_widget(widget_suite)            
            self._update_suite_ui()
        
        
        
        self.logger.debug(f'created Model {self.name}')
        
    def _attach_widget(self, widget):
        """Identify the widget children and assign pointers to myself using a recursive search."""
        log =self.logger.getChild('attach_widget')
        d = dict()
        
        # Loop through the widget dictionary and assign the widgets to the model.
        #log.debug(f'iterating through widget dictionary w/ {len(self.widget_d)} entries') 
        for name, widget_type in self.widget_d.items():
            # Recursive search: findChild is recursive by default in PyQt.
            child_widget = widget.findChild(widget_type, name)
            
            assert isinstance(child_widget, widget_type), f'failed to find widget: {name}'
            setattr(self, name, child_widget)
            d[name] = {'name': name, 'widget': child_widget}
            
        #log.debug(f'attached {len(d)} widgets')
        
        self.widget_suite=widget
            
 
        
    def _update_suite_ui(self):
        """update hte ui with the metadata"""
        self.label_mod_modelid.setText('%2d'%self.modelid)
        self.label_mod_asset.setText(self.asset_label)
        self.label_mod_consq.setText(self.consq_label)
        self.label_mod_status.setText(self.status_label)
        
        if self.status_label=='complete':
            self.progressBar_mod.setValue(100)
        else:
            self.progressBar_mod.setValue(0)
            
            
    def launch_config_ui(self):
        """launch the configuration dialog"""
        
        dial = self.parent.Model_config_dialog
        #check that the dialog is already closed
        assert not dial.isVisible(), 'dialog is already open!'
        
        #load the model into the dialog
        dial._load_model(self)
        
        #launch teh dialog
        dial.show()
    
    def run_model(self):
        """run the risk model"""
        
    def __exit__(self):
        self.logger.debug(f'destroying {self.name}')
        
        #remove the widget
        #get the parent la yout of the widget
        parent = self.widget_suite.parent()
        parent.removeWidget(self.widget_suite)
        self.widget_suite.deleteLater()
        
        del self
        

def _get_proj_meta_d(log, 
 
                   ):
    """database metadata for tracking progress of db edits
    
 
    """
    
    d = {
 
            'script_name':[os.path.basename(__file__)],
            'script_path':[os.path.dirname(__file__)],
            'now':[datetime.now()], 
            'username':[os.getlogin()], 

            'cancurve_version':[__version__], 
            'python_version':[sys.version.split()[0]],
            'platform':f"{platform.system()} {platform.release()}"            
            
            }
    #add qgis
    try:
        from qgis.core import Qgis
        d['qgis_version'] = Qgis.QGIS_VERSION
    except Exception as e:
        log.warning(f'failed to retrieve QGIS version\n    {e}')
        
 
    return d

def _update_proj_meta(log, conn, meta_d=dict()):
    
    #retrieve data
    d = _get_proj_meta_d(log)
    d.update(meta_d) #overwrite/update
    
    #push to database
    proj_meta_df = pd.DataFrame(d)
    proj_meta_df.to_sql('project_meta', conn, if_exists='append', index=False)    
    log.debug(f'updated \'project_meta\' w/ {proj_meta_df.shape}')
    return proj_meta_df
        
        