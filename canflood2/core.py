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
from .assertions import assert_projDB_fp, assert_hazDB_fp, assert_df_matches_projDB_schema
from .parameters import (
    projDB_schema_modelTables_d, project_db_schema_d,  
    )
from .hp.basic import view_web_df as view
from .hp.sql import get_table_names, pd_dtype_to_sqlite_type
from . import __version__


#===============================================================================
# CLASSES--------
#===============================================================================


class ModelNotReadyError(Exception):
    """Exception raised when the model is not ready to run."""
 


class Model_run_methods(object):
    """organizer for the model run methods"""
    
    def run_model(self,
                  projDB_fp=None,
                  ):
        """run the model"""
 
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('run_model')
        
        self.assert_is_ready(logger=log)
 
        
        if projDB_fp is None:
            projDB_fp = self.parent.get_projDB_fp()
        
        
        log.info(f'running model from {os.path.basename(projDB_fp)}') 
        
        assert_projDB_fp(projDB_fp, check_consistency=True)
        
 
    
        #=======================================================================
        # smaple rasters
        #=======================================================================
        self.r01_build_table_finv(projDB_fp)
        
    def r01_build_table_finv(self, projDB_fp=None,):
        """build the asset inventory table"""
        log = self.logger.getChild('r01_build_table_finv')
        
        #=======================================================================
        # defaults
        #=======================================================================
 
            
        model = self.model
        assert not model is None, 'no model loaded'
        
        log.info(f'building asset inventory table for model {model.name}')
        
        #=======================================================================
        # #get the asset inventory layer
        #=======================================================================
        vlay = self.comboBox_finv_vlay.currentLayer()
        assert not vlay is None, 'no asset inventory layer selected'
        
        #=======================================================================
        # #get the field names
        #=======================================================================
        d = dict()
        for comboBox, fn_str in {
            self.mFieldComboBox_cid:'xid',
            self.mFieldComboBox_AI_01_scale:'f0_scale',
            self.mFieldComboBox_AI_01_tag:'f0_tag',
            self.mFieldComboBox_AI_01_elev:'f0_elev',
            self.mFieldComboBox_AI_01_cap:'f0_cap',
            }.items():
            
            d[fn_str] = comboBox.currentField()
            
        #=======================================================================
        # #build the table
        #=======================================================================
        model.build_table_finv(vlay, d, projDB_fp=projDB_fp)
        
        log.info(f'finished building asset inventory table for model {model.name}')
        
        #=======================================================================
        # #update the labels
        #=======================================================================
        self._update_model_labels(model=model)
        
        #=======================================================================
        # #update the model widget labels
        #=======================================================================
        self.parent._update_model_widget_labels(model=model)
        
        #=======================================================================
        # #update the model index
        #=======================================================================
        self.parent.update_model_index_dx(model, logger=log)
        
        log.info(f'finished building asset inventory table for model {model.name}')
        
        return True
    
    
class Model(Model_run_methods):
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

    """
    status = 'initialized'
    asset_label=''
    consq_label=''
    
    #reference to the model config dialog
    #detaches on Model_config_dialog._custom_cleanup()
    Model_config_dialog=None 
    
    result_ead=None
    param_d=None
 
    
    def __init__(self,                  
                 parent=None, 
                 #widget_suite=None, 
                  
                 category_code='c1', 
                 modelid=0, logger=None,
                 ):
 
        self.parent=parent #Main_dialog
        self.category_code = category_code
        self.modelid = int(modelid)
        self.name = f'{category_code}_{modelid}'
        self.logger = logger.getChild(self.name)
        
        self.logger.debug(f'initialized')
        
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
        
        s['result_ead'] = self.result_ead if self.result_ead is not None else np.nan

 
        
        #=======================================================================
        # post
        #=======================================================================
 
        s.name=(modelid, category_code) #rename for multindex
        assert not None in s.values
        assert not 'nan' in s.values
        return s
        

 

    def get_table_names(self, *table_names, result_as_dict=False):
        """Return the matching table names for this model."""
        if result_as_dict:
            raise NotImplementedError()
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
    
    
    def get_model_tables_all(self, projDB_fp=None, result_as_dict=True):
        """load all tables for this model"""
        table_names_d = self.get_table_names_all(projDB_fp=projDB_fp, result_as_dict=True)
        
        #=======================================================================
        # some tables
        #=======================================================================
        if len(table_names_d)>0:
        
            tables_l = self.parent.projDB_get_tables(*table_names_d.values(), 
                                                     projDB_fp=projDB_fp, result_as_dict=False)
            
            if len(table_names_d)==1:
                tables_l = [tables_l]
            
            if result_as_dict:
                return dict(zip(table_names_d.keys(), tables_l))
            else:
                return tables_l
        
        #=======================================================================
        # no tables
        #=======================================================================
        else:
            if result_as_dict:
                return dict()
            else:
                return None
        
        
        
 
        return 
        
 

    
    def set_tables(self, df_d, **kwargs):
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
        result =  self.parent.projDB_set_tables(df_d_recast, template_prefix=f'model_{self.name}_', **kwargs)
        
        #=======================================================================
        # #handle updates
        #=======================================================================
        names_d = dict(zip(df_d.keys(), table_names ))
        for template_name, full_name in names_d.items():
            if template_name=='table_parameters':
                self.parent.update_model_index_dx(self)
                self.update_parameter_d()
                
            #add the table name to the parameters
            elif template_name in projDB_schema_modelTables_d.keys():
                self.set_parameter_value(template_name, full_name)
 
            else:
                raise IOError(f'unknown table name: {template_name}')
 
 
        self.compute_status() 
        return result
    
    def get_parameter_value(self, varName, projDB_fp=None):
        """wrapper to get a single project parameter value
        
        could set the parameters as a dictionary for faster retrival
            but then we need to worry about updating....
        """
        param_df = self.get_table_parameters(projDB_fp=projDB_fp)
        return param_df.loc[param_df['varName']==varName, 'value'].values[0]
    
    def set_parameter_value(self, varName, value, projDB_fp=None):
        """wrapper to set a single project parameter value"""
        param_df = self.get_table_parameters(projDB_fp=projDB_fp)
        param_df.loc[param_df['varName']==varName, 'value'] = value
        
        self.set_tables({'table_parameters':param_df}, projDB_fp=projDB_fp)
        
    def update_parameter_d(self, **kwargs):
        """set the parameters as a dictionary for faster retrival
        
        omitting blanks from container
        """
        df = self.get_table_parameters(**kwargs)
        """
        view(df)
        """
        self.param_d = df.set_index('varName')['value'].dropna().to_dict()
        
    
    
    

    def _get_status(self, param_df=None):
        """determine the status of the model
        
        
        
        
        status values
            initialized - value before _get_status is called
            incomplete – Implies the template is still in an unfinished, configurable state.
            ready – all ui components completed
            failed – Clearly denotes that a model run has encountered an error.
            complete – Conveys that the model run has finished successfully.
            
        """
        if param_df is None:
            param_df = self.get_table_parameters()
            
        status=None
        msg=None
        #=======================================================================
        # parameters
        #=======================================================================
        #check if all of the required parameters are populated
        param_df_required = param_df.loc[param_df['required']].loc[:, ['varName', 'value']]  
        bx = param_df_required['value'].isna()
        
        if bx.any():
            status = 'incomplete'
            
            msg = f'missing required parameters: \n    {param_df_required.loc[bx, "varName"].tolist()}'
 
            
            
        else:
            """performing checks in sequence for some redundancy
            i.e., not simply checking if the result is present"""
            
            #===================================================================
            # vfunc
            #===================================================================
            
            
            #===================================================================
            # tables
            #===================================================================
            df_d = self.get_model_tables_all(result_as_dict=True)
            
            #check missing tables
            miss_l = set(projDB_schema_modelTables_d.keys()) - set(df_d.keys())
            
            if len(miss_l)>0:
                status = 'incomplete'
                msg = f'missing tables:\n    {miss_l}'
            else:
                
                #tables populated
                for table_name in projDB_schema_modelTables_d.keys():
                    
                    if df_d[table_name].shape[0]==0:
                        status = 'incomplete'
                        msg = f'empty table: {table_name}'
                        break
                    
                #===============================================================
                # ready vs. complete
                #===============================================================
                if status is None:
                    msg=None #clear from above            
     
                    #check if results have been computed
                    if pd.isnull(self.result_ead):
                        status='ready'
     
                    else:
                        status = 'complete'
 
            
        assert not status is None, 'failed to determine status'
        return status, msg

    def compute_status(self, logger=None):
        """load info from the projDB and use to determine status
        

        
        
        """
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None:logger = self.logger
        log = logger.getChild('compute_status')
 
        
        #=======================================================================
        # get status
        #=======================================================================
        status, msg = self._get_status()
            
        log.debug(f'status={status}\n    {msg}')
            
            
        #=======================================================================
        # update
        #=======================================================================
        #update the table_parameters and the model_index
        #self.set_parameter_value('status', status)
        
        #self.update_parameter_d()
        
        #update the main dialog
        try:
            self.widget_d['label_mod_status']['widget'].setText(status)
        except Exception as e:
            raise IOError(f'failed to update Main_dialog status label w/ \n    {e}')
        
        #update model config dialog
        if not self.Model_config_dialog is None:
            try:
                self.Model_config_dialog.label_mod_status.setText(status)
            except Exception as e:
                raise IOError(f'failed to update Model_config_dialog status label w/ \n    {e}')
        
            
        
            
        self.status = status
        
        return status
        
        
    def assert_is_ready(self, logger=None):
        """check if the model is ready to and provide a verbose output if not"""
        if logger is None: logger = self.logger
        log = logger.getChild('assert_is_ready')
        #=======================================================================
        # load data
        #=======================================================================
 
        param_df = self.get_table_parameters()
        
        status, msg = self._get_status(param_df=param_df)
        log.debug(f'status=\'{status}\'')
        
        #=======================================================================
        # report on non-ready status
        #=======================================================================
        if not status in ['ready', 'complete']:            
            raise ModelNotReadyError(f'model is not ready\n    {msg}')
 
        log.debug(f'model is ready`')
 

        return #no need to resturn anything
 
            


        
        
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
        
#===============================================================================
# common functions-------------------
#===============================================================================
#===============================================================================
# def df_to_sql_templated(df, table_name, conn, **kwargs):
#     """wrapper for writing a panads dataframe to a sqlite table  using the types from the template"""
#     dtype=None
#     if table_name in project_db_schema_d:
#         template_df = project_db_schema_d[table_name]
#         if not template_df is None:
#             template_df.dtypes
#===============================================================================




 
    

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


        
        