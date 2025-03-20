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
from .hp.assertions import assert_intersection, assert_series_match, assert_sqlite_table_exists

"""need some very simple functions here to workaround module dependence"""


#===============================================================================
# ASSERTIONS-------------
#===============================================================================


    

def assert_df_template_match(df, schema_df, check_dtypes=True):
    """check the df matches the schema"""
    assert isinstance(df, pd.DataFrame)
    assert isinstance(schema_df, pd.DataFrame)
    
    #compare index names
    if isinstance(df.index, pd.MultiIndex):
        if not df.index.names == schema_df.index.names:
            raise AssertionError(
            f"Index name mismatch: test \'{df.index.names}\' vs scema \'{schema_df.index.names}\'"
            ) from None
    
    elif not df.index.name == schema_df.index.name:
        raise AssertionError(
        f"Index name mismatch: test \'{df.index.name}\' vs scema \'{schema_df.index.name}\'"
        ) from None
    
    # Compare columns (you can use assert_frame_equal if order matters)
    if len(schema_df.columns)>0: #some schemas dont specify columns
        try:
            assert_intersection(df.columns, schema_df.columns)
        except Exception as e:
            raise AssertionError(f"Column mismatch\n    {e}") from None
 
    
    # Compare the string representation of dtypes for a more approximate check:
    if check_dtypes:
        actual_dtypes = df.dtypes.astype(str).sort_index()
        expected_dtypes = schema_df.dtypes.astype(str).sort_index()
        assert_series_match(expected_dtypes, actual_dtypes)
    #assert_series_equal(actual_dtypes, expected_dtypes)
    #assert actual_dtypes.equals(expected_dtypes),f"Dtype mismatch: \nactuals:\n{actual_dtypes} vs expected\n{expected_dtypes}"
    
    
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
        """
 
        dtype=template_df.dtypes.to_dict()
        
        if isinstance(template_df.index, pd.MultiIndex):
            index_col = template_df.index.names
        elif template_df.index.name is None:
            index_col = None
        else:
            index_col = template_df.index.name
 

    
    #===========================================================================
    # read
    #===========================================================================
    assert_sqlite_table_exists(conn, table_name)
    try:
        df = pd.read_sql(f'SELECT * FROM [{table_name}]', conn, dtype=dtype, index_col=index_col,  **kwargs)
    except Exception as e:
        raise IOError(f'failed to read table \'{table_name}\' from db w/ \n    {e}')
    
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
            assert_df_template_match(df, template_df, check_dtypes=False)
 
    
    #===========================================================================
    # write
    #===========================================================================
    
    
    result = df.to_sql(table_name, conn, dtype=dtype, index=write_index, if_exists=if_exists, **kwargs)
    
    assert result==len(df), f'failed to write table \'{table_name}\''
    
    return result