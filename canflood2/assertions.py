'''
Created on Mar 6, 2025

@author: cef
'''



import os, warnings
import sqlite3
import pandas as pd

from .parameters import project_db_schema_d, hazDB_schema_d

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
def assert_proj_db_fp(fp, **kwargs):
    """full check of proj_db_fp"""
    
    assert os.path.exists(fp), fp
    assert fp.endswith('.canflood2')
    
    try:
        with sqlite3.connect(fp) as conn:
            assert_proj_db(conn, **kwargs)
    
    except Exception as e:
        raise ValueError(f'project DB connection failed w/\n    {e}')
        
        
    
 

def assert_proj_db(conn,
                   expected_tables=list(project_db_schema_d.keys())):
 
    cursor = conn.cursor()

    missing_tables = []
    for table_name in expected_tables:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            missing_tables.append(table_name)

    if missing_tables:
        raise AssertionError(f"Missing tables in project database: {', '.join(missing_tables)}")
    
    
#===============================================================================
# hazard datab ase------
#===============================================================================
def assert_haz_db_fp(fp, **kwargs):
    """full check of proj_db_fp"""
    
    assert os.path.exists(fp), fp
    assert fp.endswith('.db')
    
    try:
        with sqlite3.connect(fp) as conn:
            assert_haz_db(conn, **kwargs)
    
    except Exception as e:
        raise ValueError(f'hazard DB connection failed w/\n    {e}')
    
    
    
    
    
def assert_haz_db(conn,expected_tables=list(hazDB_schema_d.keys())):
 
    cursor = conn.cursor()

    missing_tables = []
    for table_name in expected_tables:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            missing_tables.append(table_name)

    if missing_tables:
        raise AssertionError(f"Missing tables in hazard database: {', '.join(missing_tables)}")