'''
Created on Mar 18, 2025

@author: cef

basic functions for working with the project sqlite databases

separated here for module dependence
'''
import warnings
import pandas as pd
from .parameters import project_db_schema_d, projDB_schema_modelTables_d
from .hp.sql import pd_dtype_to_sqlite_type

"""need some very simple functions here to workaround module dependence"""

#===============================================================================
# def get_pd_dtypes_from_template(template_df):
#     dtype = None
#     if template_df is not None:
#         dtype = template_df.dtypes.to_dict()
#     return dtype
#===============================================================================

def get_sqlalchemy_dtypes_from_template(template_df):
 
    return {k: pd_dtype_to_sqlite_type(v) for k, v in template_df.dtypes.items()}



def get_template_df(table_name, template_prefix=False):
    if template_prefix:
        template_name = table_name.replace(template_prefix, '')
        assert template_name in projDB_schema_modelTables_d, f'failed to find template \'{template_name}\''
        return projDB_schema_modelTables_d[template_name]
    else:
        assert table_name in project_db_schema_d, f'failed to find template \'{table_name}\''
        return project_db_schema_d[table_name]
    
 


def sql_to_df(table_name, conn, template_prefix=False, **kwargs):
    """wrapper for reading a panads dataframe from a sqlite table respecing the template types
    
    duplicated here for module dependence reasons
    """
    #===========================================================================
    # get template parameters
    #===========================================================================
    index_col, dtype=None, None
    
    template_df = get_template_df(table_name, template_prefix=template_prefix)
    
    if not template_df is None:        
 
        dtype=template_df.dtypes.to_dict()
 
        index_col = template_df.index.name
 
            
    
    #===========================================================================
    # read
    #===========================================================================

    try:
        df = pd.read_sql(f'SELECT * FROM [{table_name}]', conn, dtype=dtype, index_col=index_col,  **kwargs)
    except Exception as e:
        raise IOError(f'failed to read table \'{table_name}\' from db w/ \n    {e}')
    
    return df


def df_to_sql(df, table_name, conn, template_prefix=False, **kwargs):
    """wrapper for writing a panads dataframe to a sqlite table respecing the template types"""
 
    
    #===========================================================================
    # data checks
    #===========================================================================
    if len(df)==0:
        warnings.warn(f'attempting to write empty dataframe to table \'{table_name}\'')
        
    if df.isin(['nan']).any().any():
        raise AssertionError(f'found nan in {table_name}')
    
    #check the index is unique
    if df.index.has_duplicates:
        raise AssertionError(f'found duplicate index values in \'{table_name}\'')
    
    #===========================================================================
    # get template parameters
    #===========================================================================
    write_index=False
    dtype=None
    
    template_df = get_template_df(table_name, template_prefix=template_prefix)
    
    if not template_df is None:
        dtype = get_sqlalchemy_dtypes_from_template(template_df)
        
        if template_df.index.name is None:
            write_index=False
        else:
            write_index=True
 
        
            
    
    #===========================================================================
    # write
    #===========================================================================
    
    
    result = df.to_sql(table_name, conn, dtype=dtype, index=write_index, **kwargs)
    
    assert result==len(df), f'failed to write table \'{table_name}\''
    
    return result