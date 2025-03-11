'''
Created on Mar 6, 2025

@author: cef
'''
import os, sys, platform, sqlite3
import pandas as pd
from datetime import datetime

import numpy as np

#===============================================================================
# IMPORTS-----
#===============================================================================
from .assertions import assert_projDB_fp, assert_hazDB_fp
from .parameters import (
    projDB_schema_modelTables_d, load_vfunc_to_df_d,
    )
from .hp.basic import view_web_df as view
from .hp.sql import get_table_names
from . import __version__


#===============================================================================
# CLASSES--------
#===============================================================================
class Model(object):
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
    status = 'initialized'
    asset_label=''
    consq_label=''
    
    
    widget_suite = None
    
    result_ead=np.nan
 
    
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
                'name':self.name,
                #'status':self.status,
                }
        
    def get_model_index_ser(self,
                            param_df=None,
                             **kwargs):
        """get row from model index for this model
        
        we assume the UI has been written to hte projDB
        """
        #model_index_dx = self.parent.get_model_index_dx()
        modelid = self.modelid
        category_code = self.category_code
        
        """no... pull from teh parameters table (master data soource)
        if (modelid, category_code) in model_index_dx.index:
            return model_index_dx.loc[(modelid, category_code)]
        else:
            return None
        """
        #=======================================================================
        # from parameters import table
        #=======================================================================
        if param_df is None:
            param_df = self.get_table_parameters()
            
        try:
            s = param_df[param_df['model_index']].set_index('varName')['value']
        except Exception as e:
            raise IOError(f'failed to get model index data from parameters table\n    {e}')
        
        
        #=======================================================================
        # table names
        #=======================================================================
        table_names_d = {k:np.nan for k in projDB_schema_modelTables_d.keys()}
        table_names_d.update(self.get_table_names_all(result_as_dict=True))
        
        s = pd.concat([s, pd.Series(table_names_d)], axis=0) 
        
        #=======================================================================
        # results
        #=======================================================================
        s['result_ead'] = self.result_ead
 
        
        #=======================================================================
        # post
        #=======================================================================
        s.name=(modelid, category_code) #rename for multindex
        assert not 'nan' in s.values
        return s
        

 

    def get_table_names(self, *table_names):
        template_names = projDB_schema_modelTables_d.keys()
        for tn in table_names:
            assert tn in template_names, f'bad table name: {tn}'
    
        result = tuple(f'model_{self.name}_{k}' for k in table_names)
        return result[0] if len(result) == 1 else result

 
 

    def get_table_names_all(self, projDB_fp=None, result_as_dict=False):
        """Return all available matching table names."""
        if projDB_fp is None:
            projDB_fp = self.parent.get_projDB_fp()
    
        with sqlite3.connect(projDB_fp) as conn:
            table_names = get_table_names(conn)
            match_l = [k for k in table_names if f'model_{self.name}' in k]
    
        if result_as_dict:
            return {k.replace(f'model_{self.name}_', ''): k for k in match_l}
        else:
            return match_l

    
    def get_tables(self,*table_names, **kwargs):
        """load model specific tables from generic table names"""        
        return self.parent.projDB_get_tables(self.get_table_names(*table_names), **kwargs)
    
    def get_table_parameters(self, **kwargs):
        df_raw = self.get_tables('table_parameters', **kwargs)
        
        return format_table_parameters(df_raw)
    
    
    def get_model_tables_all(self, projDB_fp=None, **kwargs):
        """load all tables for this model"""
        table_names = self.get_table_names_all(projDB_fp=projDB_fp)
 
        return self.parent.projDB_get_tables(*table_names, projDB_fp=projDB_fp, **kwargs)
        
 

    
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
        result =  self.parent.projDB_set_tables(df_d_recast, **kwargs)
        
        #update hte model index
        if 'table_parameters' in df_d.keys():
            self.parent.update_model_index_dx(self)
            
        return result
    
    def set_parameter_value(self, varName, value, projDB_fp=None):
        """wrapper to set a single project parameter value"""
        param_df = self.get_table_parameters(projDB_fp=projDB_fp)
        param_df.loc[param_df['varName']==varName, 'value'] = value
        
        self.set_model_tables({'table_parameters':param_df}, projDB_fp=projDB_fp)
        
    
    
    
    def compute_status(self):
        """load info from the projDB and use to determine status"""
        status='initialized'
        
        
 
        param_df = self.get_table_parameters()
        
        #check if all of the required parameters are populated        
        null_cnt = param_df.loc[param_df['required'], 'value'].isna().sum()
        
        if null_cnt>0:
            status='incomplete'
        else:
            status='ready'
            
            #check if results have been computed
            raise NotImplementedError('need to implement this')
            df_d = self.get_tables_all(use_templated_names=True)
            
            
            
        #=======================================================================
        # update
        #=======================================================================
        #update the table_parameters and the model_index
        self.set_parameter_value('status', status)
        
            
        self.status = status
 
            


        
        
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
        
 

def format_table_parameters(df_raw):
    return df_raw.copy().astype({'required':bool, 'model_index':bool}).fillna(np.nan)

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


        
        