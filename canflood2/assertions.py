'''
Created on Mar 6, 2025

@author: cef
'''



import os, warnings
import sqlite3
import pandas as pd

from .parameters import project_db_schema_d, hazDB_schema_d, project_db_schema_modelSuite_d

#===============================================================================
# helpers--------
#===============================================================================
def _assert_sqlite_table_exists(conn, table_name): 
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name, ))
    result = cursor.fetchone()
    if not result:
        raise AssertionError(f"Table '{table_name}' not found in database") # Check if DRF table exists
    
    
    
    

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
        raise ValueError(f'project DB connection failed w/\n    {e}')
        
        
    
 

def assert_projDB_conn(conn,
                   expected_tables=list(project_db_schema_d.keys()),
                   check_consistency=False,
                   ):
 
    cursor = conn.cursor()

    missing_tables = []
    for table_name in expected_tables:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            missing_tables.append(table_name)

    if missing_tables:
        raise AssertionError(f"Missing tables in project database: {', '.join(missing_tables)}")
    
    if check_consistency:
        #=======================================================================
        # #check the model_index matches the model tables
        #=======================================================================
        table_name = '03_model_suite_index'
        
        dx = pd.read_sql(f'SELECT * FROM [{table_name}]', conn)
        dx['modelid'] = dx['modelid'].astype(str)
        dx = dx.set_index(['modelid', 'category_code'])
        
        if len(dx)>0:
            dx.loc[:, project_db_schema_modelSuite_d.keys()]
            raise NotImplementedError(f'need to check model tables against {table_name}')
        
    
    
    
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
def assert_eventMeta_df(df):
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

        
 









 