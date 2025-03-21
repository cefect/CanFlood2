


'''
Created on Mar 6, 2025

@author: cef
'''



import os, warnings
import sqlite3
import pandas as pd
from pandas.testing import assert_series_equal, assert_frame_equal


from .hp.assertions import assert_intersection, assert_series_match, assert_sqlite_table_exists

from .db_tools import (
    sql_to_df, assert_df_template_match,
    )
    
from .parameters import (
    project_db_schema_d, hazDB_schema_d, projDB_schema_modelTables_d,
 
    )


from .hp.sql import get_table_names
from .hp.vfunc import load_vfunc_to_df_d, vfunc_df_to_dict, vfunc_cdf_chk_d
from .hp.basic import view_web_df as view
from .hp.Q import get_unique_layer_by_name

#===============================================================================
# helpers--------
#===============================================================================

    
    

 


def assert_layerName_in_project(layer_name, layer_type=None):
    result = get_unique_layer_by_name(layer_name, layer_type=layer_type)
    if result is None:
        raise AssertionError(f"Layer '{layer_name}' not found in project") from None
                                    
    

#===============================================================================
# Project database---------
#===============================================================================
def assert_projDB_fp(fp, **kwargs):
    """full check of proj_db_fp"""
    
    assert os.path.exists(fp), fp
    assert fp.endswith('.canflood2')
    
    try:
        with sqlite3.connect(fp) as conn:
            assert_projDB_conn(conn, **kwargs)
    
    except Exception as e:
        raise ValueError(f'projDB failed validation w/ \n    {e}')
        
        
    
 

def assert_projDB_conn(conn,
                   expected_tables=list(project_db_schema_d.keys()),
                   check_consistency=False,
                   ):
 
    cursor = conn.cursor()

 

    df_d = dict()
    missing_tables = []
    for table_name in expected_tables:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            missing_tables.append(table_name)
            
        df_d[table_name] = sql_to_df(table_name, conn)
        
        assert_df_matches_projDB_schema(table_name,df_d[table_name])

    if missing_tables:
        raise AssertionError(f"Missing tables in project database: {', '.join(missing_tables)}")
    
    if check_consistency:
        
        all_table_names = get_table_names(conn)
        #=======================================================================
        # #check the model_index matches the model tables
        #=======================================================================
        table_name = '03_model_suite_index'
        
        dx = df_d[table_name].copy()
        #dx['modelid'] = dx['modelid'].astype(str)
        dx = dx.set_index(['modelid', 'category_code'])
        
        if len(dx)>0:
            tables_dx = dx.loc[:, projDB_schema_modelTables_d.keys()] 
            
            """
            view(tables_dx)
            view(dx)
            for k in all_table_names:
                if 'vfunc_index' in k:
                    print(k)
            
            """
            
            #flatten into a series
            for indexers, table_name in tables_dx.stack().dropna().items():
                if not table_name in all_table_names:
                    raise AssertionError(f'{indexers} not found in tables')
                
        #=======================================================================
        # check there are no orphaned tables
        #=======================================================================
        #identify all tables matching the model_name search pattern
        model_table_names = [table_name for table_name in all_table_names if table_name.startswith('model_')]
        
        if not len(model_table_names) == 0:
            assert len(dx)>0, f'no model tables found, but model_index table not empty'
        
            if not set(model_table_names).issubset(tables_dx.values.flatten()):
                raise AssertionError(f'orphaned model tables: {set(model_table_names) - set(tables_dx.values.flatten())}')
            
            
        #=======================================================================
        # vfuncs
        #=======================================================================
        #check the index matches the data
        table_name = '06_vfunc_index'
        index_df = df_d[table_name].copy()
        
        if len(index_df)>0:
            data_dx = df_d['07_vfunc_data'].copy().set_index(['tag', 'exposure'])
            assert len(data_dx)>0, 'no data in vfunc_data'
            
            #check the index matches the data
            assert set(index_df.index) == set(data_dx.index.unique('tag')), f'index mismatch'
        else:
            assert len(df_d['07_vfunc_data']) == 0, 'no index but data found'
            
 
        
            
def assert_df_matches_projDB_schema(table_name, actual_df, **kwargs):
    """compare the df to the schema"""
    assert isinstance(actual_df, pd.DataFrame)
    assert table_name in project_db_schema_d.keys(), f"table name \'{table_name}\' not found in schema"
    
    schema_df = project_db_schema_d[table_name]
    
 
    if schema_df is not None:
        try:
            assert_df_template_match(actual_df, schema_df, **kwargs)
            """
            schema_df.index
            """
        except Exception as e:
            raise AssertionError(f"table '{table_name}' schema mismatch:\n    {e}") from None
    
    

    
#===============================================================================
# hazard datab ase------
#===============================================================================
def assert_hazDB_fp(fp, **kwargs):
    """full check of proj_db_fp"""
    
    assert isinstance(fp, str), 'expected a string, got %s' % type(fp)
    assert os.path.exists(fp), fp
    assert fp.endswith('.db')
    
    try:
        with sqlite3.connect(fp) as conn:
            assert_hazDB_conn(conn, **kwargs)
    
    except Exception as e:
        raise ValueError(f'hazard DB connection failed w/\n    {e}')
    
    
    
    
    
def assert_hazDB_conn(conn,expected_tables=list(hazDB_schema_d.keys())):
 
    cursor = conn.cursor()

    missing_tables = []
    for table_name in expected_tables:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            missing_tables.append(table_name)

    if missing_tables:
        raise AssertionError(f"Missing tables in hazard database: {', '.join(missing_tables)}")
    
    
#===============================================================================
# hazard event metadata
#===============================================================================
def xxx_assert_eventMeta_df(df):
    """use the generic assertion"""
    """check this is an eventMeta_df"""
    assert isinstance(df, pd.DataFrame)
    #check the column names and dtypes match that of the schema

    assert set(df.columns) == set(hazDB_schema_d['05_haz_events'].columns), \
        f"Column mismatch: expected {set(hazDB_schema_d['05_haz_events'].columns)}, got {set(df.columns)}"
    
    assert all(df.dtypes == hazDB_schema_d['05_haz_events'].dtypes), \
        f"Dtype mismatch: expected {hazDB_schema_d['05_haz_events'].dtypes}, got {df.dtypes}"
        

    # Check if there are any empty strings (instead of pd.NA)
    violating_columns = df.columns[df.isin(['']).any()].tolist()
    violating_counts = df.isin(['']).sum()
    
    if violating_columns:
        details = ', '.join([f"{col}: {violating_counts[col]}" for col in violating_columns])
        raise AssertionError(f"Empty strings found in eventMeta_df in columns: {details}")

        
#===============================================================================
# INPUT DATA----------
#===============================================================================
import os
import pandas as pd

def assert_vfunc_fp(fp, msg=''):
    """
    Check the vfunc file path and validate its contents.

    Parameters:
        fp (str): The Excel file path.
        msg (str): Additional context message.

    Raises:
        AssertionError: With details including the file path if a check fails.
    """
    if not isinstance(fp, str):
        raise AssertionError(f"Expected a string for file path, got {type(fp)}. {msg}")
    if not os.path.exists(fp):
        raise AssertionError(f"File does not exist: {fp}. {msg}")
    
    try:
        vfunc_df_d = load_vfunc_to_df_d(fp)
    except Exception as e:
        raise AssertionError(f"Failed to read Excel file at '{fp}'. Error: {e}. {msg}")
    
    try:
        assert_vfunc_df_d(vfunc_df_d)
    except Exception as e:
        raise AssertionError(f"bad vfunc\n    {fp}\n    {e}\n    {msg}")

def assert_vfunc_df_d(df_d):
    """
    Validate that the Excel file was read as a dictionary of DataFrames,
    and perform checks on each sheet.

    Parameters:
        df_d (dict): Dictionary of DataFrames from the Excel file.
        fp (str): The file path for context.

    Raises:
        AssertionError: If a sheet fails validation, including its name.
    """
    if not isinstance(df_d, dict):
        raise AssertionError(f"Expected a dict of DataFrames from file   got {type(df_d)}.") from None
    
    for sheet_name, df in df_d.items():
        try:
            assert_vfunc_df(df)
        except Exception as e:
            raise AssertionError(f"Error in sheet '{sheet_name}'\n {e}") from None

def assert_vfunc_df(df_raw):
    """
        df_raw: pd.DataFrame
            >=2 column frame with
                first column (name '0') containing indexers (should loosen this)
                second column containing values
                additional columns used for 'curve_deviations'
    """
    if not isinstance(df_raw, pd.DataFrame):
        raise AssertionError(f" Input is not a DataFrame; got {type(df_raw)}.") from None
    
    assert 0 in df_raw.columns
    
    try:
        assert_vfunc_d(vfunc_df_to_dict(df_raw))
    except Exception as e:
        raise AssertionError(f"Error in DataFrame\n    {e}") from None
    
def assert_vfunc_d(crv_d):
    assert isinstance(crv_d, dict)
    
    #check the keys and the dtypes match the vfunc_cdf_chk_d
    assert set(vfunc_cdf_chk_d.keys()).issubset(set(crv_d.keys())), f'key mismatch: {set(crv_d.keys()) - set(vfunc_cdf_chk_d.keys())}'
    
    for key, val in vfunc_cdf_chk_d.items():
        assert isinstance(crv_d[key], val), f'bad type for {key}: {type(val)}'
    
  









 