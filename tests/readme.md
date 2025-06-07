# CanFlood 2 tests

tutorial test data is stored:

## tutorial_data_builder.py
 helpers for loading tutorial data to the ui
`.\canflood2\tutorials\tutorial_data_builder.py`


contains as `widget_values_lib` with parameters that are set by the `Tutorial Data Loader` widget and the pytests

Also has a function `get_test_data_filepaths_for_tutorials` for building the filepaths to the tutorial data

## Adding a new test
- create a folder with data `canflood2\tutorials\data\`
- add the parameters to `.\canflood2\tutorials\tutorial_data_builder.widget_values_lib
- update the `search_dirs` in `get_test_data_filepaths_for_tutorials`
- build the test pickles, starting with `test_01_dialog_main.test_dial_main_02_save_ui_to_project_database` with `overwrite_testdata=True`. These pickles are written to `tests\data` and used to store results from previous steps in the workflow (for better test isolation). 
