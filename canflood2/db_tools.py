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
# ASSERTIONS-------------
#===============================================================================

def assert_intersection(test, expected):
    """
    Assert that the intersection of 'test' and 'expected' is as expected.

    Parameters:
    test (iterable): The test iterable.
    expected (iterable): The expected iterable.

    Raises:
    AssertionError: If the intersection does not match the expected values.
    """
 
    test_set = set(test)
    expected_set = set(expected)
    
    if test_set != expected_set:
        missing = expected_set - test_set
        extra = test_set - expected_set
        error_message = ""
        if missing:
            error_message += f"    Missing in test: {missing}\n"
        if extra:
            error_message += f"    Unexpected in test: {extra}\n"
        raise AssertionError(error_message) from None

        
    assert test_set == expected_set, f"Expected {expected_set}, got {test_set}"




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
        raise AssertionError("Value mismatches found for common keys:\n" + diff.to_string()) from None

def assert_sqlite_table_exists(conn, table_name): 
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name, ))
    result = cursor.fetchone()
    if not result:
        raise AssertionError(f"Table '{table_name}' not found in database") # Check if DRF table exists
    

def assert_df_template_match(df, schema_df, check_dtypes=True):
    """check the df matches the schema"""
    assert isinstance(df, pd.DataFrame)
    assert isinstance(schema_df, pd.DataFrame)
    
    #compare index names
    if not df.index.name == schema_df.index.name:
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
        return projDB_schema_modelTables_d[template_name]
    else:
        assert table_name in project_db_schema_d, f'failed to find template \'{table_name}\''
        return project_db_schema_d[table_name]
    
 


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
 
        dtype=template_df.dtypes.to_dict()
 
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
        dtype = get_sqlalchemy_dtypes_from_template(template_df)
        
        if template_df.index.name is None:
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