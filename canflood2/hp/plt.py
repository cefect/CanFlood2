'''
Created on Mar 21, 2025

@author: cef


plot management for QGIS plugins

see also
    CanFLoodv1 hlpr.plot
    CanFloodv1 hlpr.plt_qt
    
    
class object that I can use (context /with management) to launch from within my dialog to handle plotting.
I'd like to avoid:
    having my matplotlib defaults affected by other plugins
    loading and configuring matplotlib when my plugin is instanced (save this for when the user wants to plot)
'''


import os
 
from PyQt5 import QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT

 
import tempfile
import hashlib
import uuid

def get_figure_hash(fig):
    """
    Compute a unique hash for a matplotlib figure's rendered contents.

    The figure is saved into a temporary directory as a PNG image,
    and an MD5 hash is computed on the file's binary data.
    
    If an error occurs during this process, a random unique hash is returned.

    Parameters:
        fig (matplotlib.figure.Figure): The matplotlib figure to hash.

    Returns:
        str: The first 6 hexadecimal digits of the MD5 hash, or a random hash on error.
    """
    try:
        # Create a temporary directory that will be cleaned up automatically.
        with tempfile.TemporaryDirectory() as tmpdirname:
            tmpfile = os.path.join(tmpdirname, "temp_fig.png")
            fig.savefig(tmpfile, format='png')
            with open(tmpfile, "rb") as f:
                image_data = f.read()
            hash_s = hashlib.md5(image_data).hexdigest()[:6]
            return hash_s
    except Exception as e:
        # If something goes wrong, return a random unique hash.
        return uuid.uuid4().hex[:6]



class PltWindow(QtWidgets.QMainWindow):
    def __init__(self, figure, out_dir=None, parent=None):
        """
        Create a Qt window embedding the given matplotlib figure.
        
        If no output directory is provided, the current working directory is used.
        """
        super().__init__(parent)
        import matplotlib

        if out_dir is None:
            out_dir = os.getcwd()
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        matplotlib.rcParams['savefig.directory'] = out_dir

        # Set window title based on the figure's suptitle if available.
        try:
            title = figure._suptitle.get_text() if figure._suptitle is not None else "Plot"
        except AttributeError:
            title = "Plot"
        self.setWindowTitle('Plot: ' + title[:15])

        # Create main widget and layout.
        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        layout = QtWidgets.QVBoxLayout(self._main)

        # Create and add the matplotlib canvas.
        canvas = FigureCanvasQTAgg(figure)
        layout.addWidget(canvas)

        # Add the navigation toolbar.
        self._toolbar = NavigationToolbar2QT(canvas, self)
        self.addToolBar(self._toolbar)
