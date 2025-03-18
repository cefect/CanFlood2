


'''
Created on Mar 6, 2025

@author: cef
'''



import os, warnings
import sqlite3
import pandas as pd
from pandas.testing import assert_series_equal, assert_frame_equal



from .db_tools import sql_to_df
from .parameters import (
    project_db_schema_d, hazDB_schema_d, projDB_schema_modelTables_d,
 
    )


from .hp.sql import get_table_names
from .hp.vfunc import load_vfunc_to_df_d, vfunc_df_to_dict, vfunc_cdf_chk_d
from .hp.basic import view_web_df as view

#===============================================================================
# helpers--------
#===============================================================================
def _assert_sqlite_table_exists(conn, table_name): 
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name, ))
    result = cursor.fetchone()
    if not result:
        raise AssertionError(f"Table '{table_name}' not found in database") # Check if DRF table exists
    
    

 

#===============================================================================
# BASIC-------------
#===============================================================================
def assert_df_template_match(df, schema_df, check_dtypes=True):
    """check the df matches the schema"""
    assert isinstance(df, pd.DataFrame)
    assert isinstance(schema_df, pd.DataFrame)
    
    # Compare columns (you can use assert_frame_equal if order matters)
    assert set(df.columns) == set(schema_df.columns), (
        f"Column mismatch: {set(df.columns) - set(schema_df.columns)}")
    
    # Compare the string representation of dtypes for a more approximate check:
    if check_dtypes:
        actual_dtypes = df.dtypes.astype(str).sort_index()
        expected_dtypes = schema_df.dtypes.astype(str).sort_index()
        assert_series_match(expected_dtypes, actual_dtypes)
    #assert_series_equal(actual_dtypes, expected_dtypes)
    #assert actual_dtypes.equals(expected_dtypes),f"Dtype mismatch: \nactuals:\n{actual_dtypes} vs expected\n{expected_dtypes}"
    

def assert_series_match(expected_series, actual_series):
    """an easier to read implementation of pd.testing.assert_series_equal"""
    # Determine the intersecting indexes.
    common_index = expected_series.index.intersection(actual_series.index)
    assert len(common_index) > 0, 'no common indexes found'
# Subset both series to only include intersecting keys.
    filtered_expected_series = expected_series.loc[common_index]
    filtered_actual_series = actual_series.loc[common_index]
# Compare the filtered series using pandas' compare().
    diff = filtered_expected_series.compare(filtered_actual_series, result_names=("expected", "actual"))
    if not diff.empty:
        raise AssertionError("Value mismatches found for common keys:\n" + diff.to_string())
    
    

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
    #get_df = lambda table_name: pd.read_sql(f'SELECT * FROM [{table_name}]', conn)
    get_df = lambda table_name: sql_to_df(table_name, conn)

    missing_tables = []
    for table_name in expected_tables:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            missing_tables.append(table_name)
            
 
        
        assert_df_matches_projDB_schema(table_name, get_df(table_name))

    if missing_tables:
        raise AssertionError(f"Missing tables in project database: {', '.join(missing_tables)}")
    
    if check_consistency:
        
        all_table_names = get_table_names(conn)
        #=======================================================================
        # #check the model_index matches the model tables
        #=======================================================================
        table_name = '03_model_suite_index'
        
        dx = get_df(table_name) 
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
        index_df = get_df(table_name)
        
        if len(index_df)>0:
            data_dx = get_df('07_vfunc_data').set_index(['tag', 'exposure'])
            assert len(data_dx)>0, 'no data in vfunc_data'
            
            #check the index matches the data
            assert set(index_df['tag']) == set(data_dx.index.unique('tag')), f'index mismatch'
        else:
            assert len(get_df('07_vfunc_data')) == 0, 'no index but data found'
            
 
        
            
def assert_df_matches_projDB_schema(table_name, actual_df, **kwargs):
    """compare the df to the schema"""
    assert isinstance(actual_df, pd.DataFrame)
    assert table_name in project_db_schema_d.keys(), f"bad table_name: {table_name}"
    
    schema_df = project_db_schema_d[table_name]
    
 
    if schema_df is not None:
        try:
            assert_df_template_match(actual_df, schema_df, **kwargs)
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
    
  









 