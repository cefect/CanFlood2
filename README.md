[![Documentation Status (dev)](https://readthedocs.org/projects/canflood2/badge/?version=dev)](https://canflood.readthedocs.io/en/dev/)
[![Documentation Status (latest)](https://readthedocs.org/projects/canflood2/badge/?version=latest)](https://canflood.readthedocs.io/en/latest/)


# CanFlood2
 
Open source flood risk modelling toolbox for Canada v2



![alt text](https://github.com/cefect/CanFlood2/blob/main/canflood2/img/logo_20210510_22x22.png)


tested against QGIS 3.34.14 and Qt 5.15.13

## Documentation

[Documentation](https://canflood2.readthedocs.io/en/latest/#) is provided in English for the latest, development, and archive versions. 

## Updates

v2.0.0 prototype with the following features:
- *Welcome*: tutorial data loader. NOTE: this also loads a complete project database.
- *Project Setup*: create/load project database file. select Study Area (not used) and DEM
- *Hazard*: specify metadata, select hazard events from loaded raster layers, populate event data. Eventually, support of export/import of just the hazard data will be added (for easier hazard scenario comparisons).
- *Model Suite*: Creating template models for each of the 7 categories and launching the model config dialog.
- *Model Configuration*: depth-dependent (L2) model setup and running. 
- *Reporting*: Generate a **Risk Curve** from a completed model. 
  




## Installation Instructions 

- Ensure the QGIS and Qt version 'tested' above is installed and working on your system ([Qgis all releases download page](https://qgis.org/downloads/)). Ensure the 'processing' plugin is installed and enabled in QGIS.  
- download the `canflood2.zip` file from the [latest release](https://github.com/cefect/CanFlood2/releases) to your local machine
- in QGIS, `Manage and Install Plugins...` > `Install from ZIP` > select the downloaded file
- we recommended to also install the **First Aid** plugin for more detailed error messages 
- we recommended to set up the QGIS Debug Log file as shown [here](https://stackoverflow.com/a/61669864/9871683)
- CanFlood2 backend and project data is implemented in SQLite relational databases. For enhanced customization and debugging, it is recommended to install a SQLite viewer + editor like [DB Browser for SQLite](https://sqlitebrowser.org/) for working with these files  


## Re-installation/updating
For best performance: follow similar steps to the above, but be sure to **Uninstall** the plugin and restart QGIS first 


## Development
see [CONTRIBUTING.md](./CONTRIBUTING.md)
