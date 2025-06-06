'''
Created on Mar 18, 2025

@author: cef

basic functions for working with the project sqlite databases

separated here for module dependence
'''
import warnings
import pandas as pd
from .parameters import project_db_schema_d, projDB_schema_modelTables_d
from .hp.sql import pd_dtype_to_sqlite_type, get_columns_names
from .hp.assertions import (
    assert_df_template_match,  assert_sqlite_table_exists, assert_intersection
    )
from .hp.pd import map_multiindex_dtypes

"""need some very simple functions here to workaround module dependence"""


#===============================================================================
# ASSERTIONS-------------
#===============================================================================


    


    
#===============================================================================
# HELPER FUNCS---------
#===============================================================================
def get_sqlalchemy_dtypes_from_template(template_df):
 
    return {k: pd_dtype_to_sqlite_type(v) for k, v in template_df.dtypes.items()}



def get_template_df(table_name, template_prefix=None):
    if not template_prefix is None:
        assert isinstance(template_prefix, str)
        template_name = table_name.replace(template_prefix, '')
        assert template_name in projDB_schema_modelTables_d, f'failed to find template \'{template_name}\''
        result =  projDB_schema_modelTables_d[template_name]
    else:
        assert table_name in project_db_schema_d, f'failed to find template \'{table_name}\''
        result =  project_db_schema_d[table_name]
        
    if not result is None: 
        #check consistency (index names are not in the column names)
        if isinstance(result.index, pd.MultiIndex):
            assert not result.index.names in result.columns, f'found index names in columns for \'{table_name}\''
        else:
            assert not result.index.name in result.columns, f'found index name in columns for \'{table_name}\''
        
    return result
    
 


def sql_to_df(table_name, conn, template_prefix=None, **kwargs):
    """wrapper for reading a panads dataframe from a sqlite table respecing the template types
    
    duplicated here for module dependence reasons
    """
    #===========================================================================
    # get template parameters
    #===========================================================================
    index_col, dtype=None, None
    
    template_df = get_template_df(table_name, template_prefix=template_prefix)
    
    if not template_df is None:        
        """
        template_df.index
        template_df.dtypes
        dtype
 
        """
 
        dtype=template_df.dtypes.to_dict()
        

 
        
        #configure the index param
        if isinstance(template_df.index, pd.MultiIndex):
            index_col = template_df.index.names
            #dtype.update(template_df.index.dtypes.to_dict()) #add the index dtypes
        elif template_df.index.name is None:
            index_col = None
        else:
            index_col = template_df.index.name
            
        #check each of these columns are also columns in the sqlite table
        if len(dtype)>0:
            if index_col is None:
                index_col_check = []
            else:
                index_col_check = [index_col] if isinstance(index_col, str) else index_col
            try:
                column_names = get_columns_names(conn, table_name)
                assert_intersection(
                    set(column_names).difference(index_col_check), 
                    dtype.keys())
            except Exception as e:
                raise AssertionError(f"template columns not found in table \n    {e}") from None
        
 

    
    #===========================================================================
    # read
    #===========================================================================
    assert_sqlite_table_exists(conn, table_name)
    try:
        df = pd.read_sql(f'SELECT * FROM [{table_name}]', conn, dtype=dtype, index_col=index_col,  **kwargs)
    except Exception as e:
        raise IOError(f'failed to read table \'{table_name}\' from db w/ \n    {e}')
    
    #===========================================================================
    # set index dtype
    #===========================================================================
    """doesnt seem to be a way to do this with pd.read_sql"""
    if not template_df is None:
        if isinstance(template_df.index, pd.MultiIndex):
            if not df.index.dtypes.to_dict() == template_df.index.dtypes.to_dict():
                df.index = map_multiindex_dtypes(df.index, template_df.index.dtypes.to_dict())
 
 
        else:
            df.index = df.index.astype(template_df.index.dtype)
    
    #===========================================================================
    # dev
    #===========================================================================
    if table_name=='03_model_suite_index':
        
        assert_df_template_match(df, template_df, check_dtypes=True)
        
        df.index.dtypes
        template_df.index.dtypes
        
        if len(df)>0:
            assert df.index.names == ['category_code', 'modelid'], f'bad index names on \'{table_name}\''
    
    #===========================================================================
    # if table_name=='06_vfunc_index':
    #     df.index.name
    #     print(f'this table is not yet supported {table_name}')
    #===========================================================================
    
    return df


def df_to_sql(df, table_name, conn, template_prefix=None,if_exists='replace', **kwargs):
    """wrapper for writing a panads dataframe to a sqlite table respecing the template types"""
 
    
    #===========================================================================
    # data checks
    #===========================================================================
    if len(df)==0:
        warnings.warn(f'attempting to write empty dataframe to table \'{table_name}\'')
        pass #do this alot w/ L1
        
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
        """what about index typessetting"""
        dtype = get_sqlalchemy_dtypes_from_template(template_df)
        
        if isinstance(template_df.index, pd.MultiIndex):
            write_index=True
            assert_df_template_match(df, template_df, check_dtypes=False)
        
        elif template_df.index.name is None:
            write_index=False
            
            assert_df_template_match(df.reset_index(drop=True), template_df, check_dtypes=False)
        else:
            write_index=True
            
            #simulating the behavior of pd.to_sql
            try:
                assert_df_template_match(df, template_df, check_dtypes=False)
            except Exception as e:
                raise AssertionError(f"passed \'{table_name}\' ({df.shape}) does not match template \n    {e}") 
 
    
    #===========================================================================
    # write
    #===========================================================================
    
    
    result = df.to_sql(table_name, conn, dtype=dtype, index=write_index, if_exists=if_exists, **kwargs)
    
    assert result==len(df), f'failed to write table \'{table_name}\''
    
    #===========================================================================
    # dev
    #===========================================================================
    if table_name=='03_model_suite_index':
        template_df.dtypes
        assert_df_template_match(df, template_df, check_dtypes=True)
        
        if len(df)>0:
            assert df.index.names == ['category_code', 'modelid'], f'bad index names on \'{table_name}\''
    
    return result