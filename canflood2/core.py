'''
Created on Mar 6, 2025

@author: cef
'''
import os, sys, platform, sqlite3
import pandas as pd
from datetime import datetime

from PyQt5.QtWidgets import QLabel, QPushButton, QProgressBar


from .assertions import assert_proj_db_fp, assert_haz_db_fp
from .parameters import project_db_schema_nested_d
from .hp.basic import view_web_df as view
from .hp.sql import get_table_names
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
                 asset_label='', consq_label='',status_label='incomplete',

                 ):
        """Constructor for the model class.
        
        Parameters
        ----------
        widget_suite : Qwidget_suite
            small 1-line control widget on the model suite tab
            NOTE: the model config dialog is controlled by the main dialog
            see self.launch_config_ui
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
        self.logger = logger.getChild(f'M.{self.name}')
        
        if not widget_suite is None:
            self._attach_widget(widget_suite)            
            self._update_suite_ui()
        
        """no... only do this when the model config has been called
        self._create_tables()
        """
        
        
        self.logger.debug(f'Model {self.name} initialized')
        
    def get_index_d(self):
        return {'category_code':self.category_code, 'modelid':self.modelid, 'category_desc':self.category_desc,
                'name':self.name}
        
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
            
    def _get_projDB_fp(self):
        fp =  self.parent.lineEdit_PS_projDB_fp.text()
        assert_proj_db_fp(fp)
        return fp
    
    def _get_hazDB_fp(self):
        fp =  self.parent.lineEdit_HZ_hazDB_fp.text()
        assert_haz_db_fp(fp)
        return fp
    
    def _get_model_tables(self,*table_names, **kwargs):
        """load model specific tables from generic table names"""        
        return self.parent.projDB_get_tables(*[f'model_{self.name}_{k}' for k in table_names], **kwargs)

    def _update_model_index(self, table_names_d, projDB_fp=None, logger=None):
        """update the model index in the project with my table names"""
        if logger is None: logger=self.logger
        log = logger.getChild('update_model_index')
        if projDB_fp is None: projDB_fp = self._get_projDB_fp()
        
        
        model_index_dx = self.parent.get_model_index_dx(projDB_fp=projDB_fp)
        
        log.debug(f'updating \'model_index\' w/ {model_index_dx.shape} and {len(table_names_d)} new entries')
        
        table_names_ser = pd.Series({**table_names_d, **self.get_index_d()})
        # Compute the expected keys: the union of the MultiIndex names and the DataFrame columns.
        expected_keys = set(model_index_dx.index.names).union(set(model_index_dx.columns.tolist()))
        # Check that the keys in the lookup Series match the expected keys.
        assert set(table_names_ser.index).issubset(expected_keys), (
        f"Mismatched keys: expected a subset of {expected_keys} but got {set(table_names_ser.index)}")
        # Extract the index values from the lookup Series using the index names.
        mi_key = tuple(table_names_ser[name] for name in model_index_dx.index.names)
        # Determine which keys to update: the ones corresponding to the DataFrame columns that are also in the Series index.
        update_keys = list(set(model_index_dx.columns).intersection(table_names_ser.index))
        # Update the row in the DataFrame at the given multi-index with the values from the lookup Series.
        model_index_dx.loc[mi_key, update_keys] = table_names_ser.loc[update_keys].values
        
        #fill blanks with nulls
        model_index_dx = model_index_dx.replace('', pd.NA)
        
        #write the update to hte project database
        with sqlite3.connect(projDB_fp) as conn:
            model_index_dx.reset_index().to_sql('03_model_suite_index', conn, if_exists='replace', index=True)
            log.debug(f'updated \'model_index\' w/ {model_index_dx.shape}')
        
        return 

    def _create_tables(self, projDB_fp=None, logger=None):
        """checking and creating tables
        
        called each time the model config is launched
        
        only adding missing tables
        """
        if logger is None: logger=self.logger
        log = logger.getChild('create_tables')
        #assert_proj_db_fp(projDB_fp) call this during _get_projDB_fp
        
        #get list of tables already in the database
        with sqlite3.connect(projDB_fp) as conn:
            existing_table_names = get_table_names(conn)
        
            #=======================================================================
            # build missing dataframes from the schema
            #=======================================================================            
            table_names_d = dict()
            df_d = dict()
            for k, v in project_db_schema_nested_d.items():
                table_name = f'model_{self.name}_{k}'
                
                if not table_name in existing_table_names:                
                    if v is None: 
                        continue #should add templates for everything?
                    else:
                        df_d[table_name] = v.copy()
                        
                    table_names_d[k] = table_name
                    
            log.debug(f'created {len(df_d)} tables from templates')
        
 
            #=======================================================================
            # write to the project datavbase
            #======================================================================= 
            for k, df in df_d.items(): 
                try:
                    df.to_sql(k, conn, if_exists='replace', index=False)
                except Exception as e:
                    raise IOError(f'failed to write \'{k}\' to project database\n    {e}')
                log.debug(f'wrote {k} w/ {df.shape}')
                
        
        #=======================================================================
        # update the model index
        #=======================================================================
        if len(table_names_d)>0:
            self._update_model_index(table_names_d, projDB_fp=projDB_fp, logger=log)
        
        
        #=======================================================================
        # udpate status
        #=======================================================================
        log.debug(f'updated project database with model tables to \n    {projDB_fp}')
        self.status_label = 'templated'
        
        
        return
        
            
            
            
        
            
            
    def launch_config_ui(self):
        """launch the configuration dialog"""
        log = self.logger.getChild('launch_config_ui')
        log.debug(f'user pushed model config for {self.name}')
        
        #check ther eis a project database
        projDB_fp = self._get_projDB_fp()
        if projDB_fp is None or projDB_fp=='':
            raise IOError('must set a project datatbase file before configuring models')
        
        #and the hazardss database
        hazDB_fp = self._get_hazDB_fp()
        if hazDB_fp is None or hazDB_fp=='':
            raise IOError('must set a hazards datatbase file before configuring models')
        
 
        #setup the project database
        self._create_tables(projDB_fp=projDB_fp, logger=self.logger)
        
        dial = self.parent.Model_config_dialog
        #check that the dialog is already closed
        assert not dial.isVisible(), 'dialog is already open!'
        
        #load the model into the dialog
        dial._load_model(self)
        
        #attach this dialog to yourself
        #allows the model to pull values from the dialog
        self.dial = dial
        
        #launch teh dialog
        dial.show()
        
        
    
    def run_model(self):
        """run the risk model"""
        
        #=======================================================================
        # build the inventory vector layer (finv)
        #=======================================================================
        
    def _get_finv(self):
        """get the asset inventory vector layer from the ui"""
        vlay = comboBox_finv_vlay.currentLayer()
        assert isinstance(vlay, QgsVectorLayer), f'bad vlay: {vlay}'
        
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

            'canflood2_version':[__version__], 
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
        
        