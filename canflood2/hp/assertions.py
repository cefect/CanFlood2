'''
Created on Mar 20, 2025

@author: cef
'''
import pandas as pd

def assert_intersection(test, expected):
    """
    Assert that the intersection of 'test' and 'expected' is as expected.

    Parameters:
    test (iterable): The test iterable.
    expected (iterable): The expected iterable.

    Raises:
    AssertionError: If the intersection does not match the expected values.
    """
 
    try:
        test_set = set(test)
    except Exception as e:
        raise AssertionError(f"Failed to convert test to set: {e}") from None
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

def assert_index_match(test_index, expected_index):
 
    
    if isinstance(test_index, pd.MultiIndex):
        assert isinstance(expected_index, pd.MultiIndex)
        if not test_index.names == expected_index.names:
            raise AssertionError(f"Index names mismatch: {test_index.names} vs {expected_index.names}")
        assert_intersection(test_index.values, expected_index.values)
        
    elif isinstance(test_index, pd.Index):
        assert isinstance(expected_index, pd.Index)
        assert test_index.name == expected_index.name
        assert_intersection(test_index, expected_index)
        
    else:
        raise AssertionError(f"unexpected index type: {type(test_index)}")
    


def assert_series_match(expected_series, actual_series):
    """an easier to read implementation of pd.testing.assert_series_equal"""
    assert isinstance(expected_series, pd.Series)
    assert isinstance(actual_series, pd.Series)
    
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