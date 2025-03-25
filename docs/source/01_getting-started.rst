.. _sec01-gettingStarted:

Getting Started
==================

The following sections will help you get started using CanFlood2.
We suggest reading these sections first before reading the :ref:`User Guide <sec02-userGuide>` or the :ref:`Tutorials <sec03-tutorials>`.


.. _sec01-install:

Installation
------------

To install CanFlood2, you first need to install QGIS, then you can install CanFlood2 from the Plugin Repository.
For detailed instructions, refer to the `project README <https://github.com/NRCan/CanFlood2/tree/main?tab=readme-ov-file#installation>`_.
For best performance, ensure you have the specified version of QGIS installed.

After installation of the plugin, the |CanFlood2_icon| icon should appear on your plugins toolbar.
If you don't see the icon, first ensure the plugin is checked on the **Installed** tab of the "**Manage and Install Plugins..**" dialog, then ensure the **plugins toolbar** is enabled by right-clicking the QGIS toolbar.

.. |CanFlood2_icon| image:: /assets/logo_20210510_22x22.png
   :align: middle
   :width: 14


.. _sec01-overview:

Overviews
-----------------------
CanFlood2 is a platform for constructing and running flood risk models for Canada.






.. _sec01-quick:

Quick-Start
-----------------------


To start working with CanFlood2, click the |CanFlood2_icon| to open the :ref:`Buildings Tool <sec02-bldgs>` dialog.


.. _fig-dialog-welcome:

.. figure:: /assets/01-dialog-welcome.png
   :alt: Welcome Tab
   :align: center
   :width: 900px

   Welcome tab of the Buildings Tool.


To use the tool to create a DDF from data for your archetypal building, first populate the **Metadata** tab with whatever information is available (see the :ref:`Tutorials <sec03-tutorials>` section for example data).
Note only fields marked with an asterisk (*) are required, but the more information you provide, the more complete your DDF will be.
To specify settings, the :ref:`Cost-Item Table <sec02-costItem>`, the :ref:`Depth-Replacement Factor (DRF) Database <sec02-DRF>`, and the :ref:`Fixed Costs <sec02-fixedCosts>` data, complete the **Data Input** tab.
Finally, the four curve creation steps can be executed from the **Create Curve** tab, ending in an export of your DDF in :ref:`CanFlood format <sec02-CanFloodFormat>`.


See the :ref:`User Guide <sec02-userGuide>` and the :ref:`Tutorials <sec03-tutorials>` section to learn more.


.. _sec01-faq:

Frequently Asked Questions
--------------------------

**Where can I find Cost-Item data for my archetype?**
    Typically this information is obtained from cost restoration experts using specialized software like Xactimate and a detailed model of the structure.

**How can I add entries to my Depth-Replacement-Factor (DRF) Database?**
    You'll need to use some software that allows editing of SQLite databases. We recommend `DB Browser for SQLite <https://sqlitebrowser.org/>`_.

**Where can I go to get help?**
    The best place to get help is the `CanFlood2 GitHub Issues <https://github.com/NRCan/CanFlood2/issues>`_ page where you can read through questions posted by others or ask your own.


**Do I really need to install an old version of QGIS to use CanFlood2?**
      No, but we recommend it for best performance. If you have a newer version of QGIS installed, you can try CanFlood2 with it, but you may experience issues.
      We do our best to keep CanFlood2 up-to-date with the latest version of QGIS.






