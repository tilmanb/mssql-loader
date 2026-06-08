import os
from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QIcon
from qgis.utils import iface
from .mssql_loader_dialog import MSSQLLoaderDialog


class MSSQLLoaderPlugin:
    """QGIS Plugin for loading spatial data from MSSQL SQL queries"""
    
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        """Create plugin menu item and toolbar button"""
        self.action = QAction("MSSQL Loader", self.iface.mainWindow())
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        self.action.setIcon(QIcon(icon_path))
        self.action.setStatusTip("Load spatial data from MSSQL SQL queries")
        self.action.triggered.connect(self.show_dialog)
        
        # Add to plugin menu
        self.iface.addPluginToMenu("Database", self.action)

    def unload(self):
        """Remove plugin from menu"""
        self.iface.removePluginMenu("Database", self.action)

    def show_dialog(self):
        """Show the MSSQL Loader dialog"""
        if not self.dialog:
            self.dialog = MSSQLLoaderDialog(self.iface.mainWindow())
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
