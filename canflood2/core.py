'''
Created on Mar 6, 2025

@author: cef
'''
import os, sys, platform, sqlite3
import pandas as pd
from datetime import datetime




from .assertions import assert_projDB_fp, assert_hazDB_fp
from .parameters import project_db_schema_modelSuite_d
from .hp.basic import view_web_df as view
from .hp.sql import get_table_names
from . import __version__


class Model_suite_helper(object):
    """skinny helper functions for dealing with an individual model 
    on the model suite tab
    
    
    went back and forth on this
        seems a slightly more convenient to instance a small class like this for each model
        needs to be very lightweight though
        and needs to be properly closed
        all configuration and running should be handled by the Model_config_dialog 
            which is instanced once
    """
    
    
    """ 
    status_label
        initialized - templated, but not configured
        incomplete – Implies the template is still in an unfinished, configurable state.
        Ready – Indicates that the model is configured and waiting to run.
        Failed – Clearly denotes that a model run has encountered an error.
        Complete – Conveys that the model run has finished successfully.
    """
    status_label = 'initialized'
    asset_label=''
    consq_label=''
    
    
    widget_suite = None
    
    def __init__(self,                  
                 parent=None, 
                 #widget_suite=None, 
                  
                 category_code='c1', 
                 modelid=0, logger=None,
                 ):
 
        self.parent=parent
        self.category_code = category_code
        self.modelid = int(modelid)
        self.name = f'{category_code}_{modelid}'
        self.logger = logger.getChild(self.name)
        
        
    def get_index_d(self):
        return {'category_code':self.category_code, 'modelid':self.modelid, 
                #'category_desc':self.category_desc,
                'name':self.name}
        
    def get_model_index_ser(self, **kwargs):
        """get row from model index for this model"""
        model_index_dx = self.parent.get_model_index_dx()
        modelid = self.modelid
        category_code = self.category_code
        
        if (modelid, category_code) in model_index_dx.index:
            return model_index_dx.loc[(modelid, category_code)]
        else:
            return None
        

 

    def get_table_names(self, *table_names):
        template_names = project_db_schema_modelSuite_d.keys()
        for tn in table_names:
            assert tn in template_names, f'bad table name: {tn}'
    
        result = tuple(f'model_{self.name}_{k}' for k in table_names)
        return result[0] if len(result) == 1 else result

 
    def get_model_tables(self,*table_names, **kwargs):
        """load model specific tables from generic table names"""        
        return self.parent.projDB_get_tables(self.get_table_names(*table_names), **kwargs)
    
    def get_model_tables_all(self, projDB_fp=None, logger=None):
        """load all model specific tables from the project database"""
        if logger is None: logger=self.logger
        log = self.logger.getChild('get_model_tables_all')
        if projDB_fp is None:
            projDB_fp = self.parent.get_projDB_fp()
            
        assert os.path.exists(projDB_fp), f'bad projDB_fp: {projDB_fp}'
            
        with sqlite3.connect(projDB_fp) as conn:
            #get the table names
            table_names = get_table_names(conn)
            
            #find all those matching my search string
            match_l = [k for k in table_names if f'model_{self.name}' in k]
            
            log.debug(f'found {len(match_l)}/{len(table_names)} matching tables')
            
            if len(match_l)>0:
                df_d = dict()
                for n in match_l:
                    df_d[n] = pd.read_sql(f'SELECT * FROM [{n}]', conn)
 
 
            else:
                df_d = dict()
                
        #close the connection
        return df_d
    
    def set_model_tables(self, df_d, **kwargs):
        """write the tables to the project database"""
        
        #recase the names

        # Get the table names
        table_names = self.get_table_names(*df_d.keys())
        
        # Ensure table_names is a list
        if isinstance(table_names, str):
            table_names = [table_names]
        
        # Recast the DataFrame dictionary with the correct table names
        df_d_recast = dict(zip(table_names, df_d.values()))
        
        # Write the tables to the project database
        return self.parent.projDB_set_tables(df_d_recast, **kwargs)

    

        
        
    def __exit__(self, exc_type, exc_value, traceback):
        """Cleanup resources when exiting the context or explicitly calling cleanup."""
        if self.logger:
            self.logger.debug(f'Exiting and destroying {self.name}')
        
 
        
        # Break any remaining circular references or held pointers:
        self.parent = None
        self.logger = None
        # You can delete attributes if needed:
        # for attr in list(self.__dict__.keys()):
        #     delattr(self, attr)
        
        # Returning False lets any exception propagate, which is standard
        return False
        
 

        

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
        
        