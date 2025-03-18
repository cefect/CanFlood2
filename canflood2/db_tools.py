'''
Created on Mar 18, 2025

@author: cef

basic functions for working with the project sqlite databases

separated here for module dependence
'''
import warnings
import pandas as pd
from .parameters import project_db_schema_d
from .hp.sql import pd_dtype_to_sqlite_type

"""need some very simple functions here to workaround module dependence"""
def get_pd_dtypes_from_schema(table_name):
    dtype=None
    if table_name in project_db_schema_d:
        template_df = project_db_schema_d[table_name]
        if not template_df is None:
            dtype = template_df.dtypes.to_dict()
            
    return dtype
    
def get_sqlalchemy_dtypes_from_schema(table_name):
    dtype=None
    if table_name in project_db_schema_d:
        template_df = project_db_schema_d[table_name]
        if not template_df is None:
            
            dtype = {k:pd_dtype_to_sqlite_type(v) for k,v in template_df.dtypes.items()}
            
    return dtype


def sql_to_df(table_name, conn, **kwargs):
    """wrapper for reading a panads dataframe from a sqlite table respecing the template types
    
    duplicated here for module dependence reasons
    """
    
    dtype=get_pd_dtypes_from_schema(table_name)

    try:
        df = pd.read_sql(f'SELECT * FROM [{table_name}]', conn, dtype=dtype, **kwargs)
    except Exception as e:
        raise IOError(f'failed to read table \'{table_name}\' from db w/ \n    {e}')
    
    return df


def df_to_sql(df, table_name, conn, **kwargs):
    """wrapper for writing a panads dataframe to a sqlite table respecing the template types"""
    """cant use this in the main module because of module dependence
    assert_df_matches_projDB_schema(table_name, df)"""
    
    #===========================================================================
    # data checks
    #===========================================================================
    if len(df)==0:
        warnings.warn(f'attempting to write empty dataframe to table \'{table_name}\'')
        
    if df.isin(['nan']).any().any():
        raise AssertionError(f'found nan in {k}')
    
    #===========================================================================
    # write
    #===========================================================================
    dtype = get_sqlalchemy_dtypes_from_schema(table_name)
    
    result = df.to_sql(table_name, conn, dtype=dtype, **kwargs)
    
    assert result==len(df), f'failed to write table \'{table_name}\''
    
    return result