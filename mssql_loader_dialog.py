from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QLabel, QLineEdit, QComboBox, QPlainTextEdit, QCheckBox,
    QTabWidget, QWidget, QSpinBox, QGroupBox
)
from PyQt5.QtCore import Qt, QTimer
from qgis.gui import QgsProjectionSelectionDialog, QgsMessageBar
from qgis.core import QgsProject, Qgis
from pprint import pprint
import traceback

from .mssql_loader_class import MSSQLLayerLoader


class MSSQLLoaderDialog(QDialog):
    """Dialog for configuring MSSQL database connections and loading spatial data into QGIS"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MSSQL Loader - Load Spatial Data from SQL Server")
        self.setGeometry(100, 100, 900, 700)
        
        self.crs = 'EPSG:25832'  # Default CRS
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout()
        
        # Create tabs for Connection and Query settings
        tabs = QTabWidget()
        
        # Connection tab
        connection_tab = QWidget()
        connection_layout = QGridLayout()
        
        # Connection type selector
        connection_layout.addWidget(QLabel("Connection Type:"), 0, 0)
        self.conn_type_combo = QComboBox()
        self.conn_type_combo.addItems(["Manual Parameters", "QGIS Named Connection"])
        self.conn_type_combo.currentTextChanged.connect(self.on_connection_type_changed)
        connection_layout.addWidget(self.conn_type_combo, 0, 1, 1, 3)
        
        # Manual connection parameters group
        self.manual_conn_group = QGroupBox("Manual Connection Parameters")
        manual_layout = QGridLayout()
        
        # Server
        manual_layout.addWidget(QLabel("Server:"), 0, 0)
        self.server_input = QLineEdit()
        self.server_input.setText("localhost")
        manual_layout.addWidget(self.server_input, 0, 1, 1, 2)
        
        # Database
        manual_layout.addWidget(QLabel("Database:"), 1, 0)
        self.database_input = QLineEdit()
        self.database_input.setText("master")
        manual_layout.addWidget(self.database_input, 1, 1, 1, 2)
        
        # Username
        manual_layout.addWidget(QLabel("Username:"), 2, 0)
        self.username_input = QLineEdit()
        self.username_input.setText("sa")
        manual_layout.addWidget(self.username_input, 2, 1, 1, 2)
        
        # Password
        manual_layout.addWidget(QLabel("Password:"), 3, 0)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        manual_layout.addWidget(self.password_input, 3, 1, 1, 2)
        
        # Driver
        manual_layout.addWidget(QLabel("Driver:"), 4, 0)
        self.driver_combo = QComboBox()
        self.driver_combo.addItems(["{SQL Server}", "{ODBC Driver 17 for SQL Server}"])
        manual_layout.addWidget(self.driver_combo, 4, 1, 1, 2)
        
        self.manual_conn_group.setLayout(manual_layout)
        connection_layout.addWidget(self.manual_conn_group, 1, 0, 3, 4)
        
        # QGIS Named Connection group
        self.qgis_conn_group = QGroupBox("QGIS Named Connection")
        qgis_layout = QGridLayout()
        qgis_layout.addWidget(QLabel("Connection Name:"), 0, 0)
        self.qgis_conn_combo = QComboBox()
        self.refresh_qgis_connections()
        qgis_layout.addWidget(self.qgis_conn_combo, 0, 1)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_qgis_connections)
        qgis_layout.addWidget(refresh_btn, 0, 2)
        self.qgis_conn_group.setLayout(qgis_layout)
        self.qgis_conn_group.setVisible(False)
        connection_layout.addWidget(self.qgis_conn_group, 1, 0, 3, 4)
        
        # Test connection button
        test_conn_btn = QPushButton("Test Connection")
        test_conn_btn.clicked.connect(self.test_connection)
        connection_layout.addWidget(test_conn_btn, 4, 0, 1, 4)
        
        connection_layout.setRowStretch(5, 1)
        connection_tab.setLayout(connection_layout)
        
        # Query tab
        query_tab = QWidget()
        query_layout = QVBoxLayout()
        
        # SQL Query editor
        query_layout.addWidget(QLabel("SQL Query:"))
        self.query_editor = QPlainTextEdit()
        self.query_editor.setPlaceholderText(
            "SELECT id, name, geom FROM table_name\n\n"
            "Note: Geometry column should be named 'geom' or will be auto-detected"
        )
        self.query_editor.setMinimumHeight(200)
        query_layout.addWidget(self.query_editor)
        
        # Layer settings
        settings_layout = QGridLayout()
        
        settings_layout.addWidget(QLabel("Layer Name:"), 0, 0)
        self.layer_name_input = QLineEdit()
        self.layer_name_input.setText("SQL Server Layer")
        settings_layout.addWidget(self.layer_name_input, 0, 1, 1, 2)
        
        settings_layout.addWidget(QLabel("Geometry Type:"), 1, 0)
        self.geom_type_combo = QComboBox()
        self.geom_type_combo.addItems(["Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon"])
        self.geom_type_combo.setCurrentText("Point")
        settings_layout.addWidget(self.geom_type_combo, 1, 1)
        
        settings_layout.addWidget(QLabel("CRS:"), 1, 2)
        self.crs_display = QLineEdit()
        self.crs_display.setText(self.crs)
        self.crs_display.setReadOnly(True)
        settings_layout.addWidget(self.crs_display, 1, 3)
        
        crs_btn = QPushButton("Select CRS")
        crs_btn.clicked.connect(self.select_crs)
        settings_layout.addWidget(crs_btn, 1, 4)
        
        settings_layout.addWidget(QLabel("Layer Type:"), 2, 0)
        self.layer_type_combo = QComboBox()
        self.layer_type_combo.addItems(["Memory Layer (Static Snapshot)", "Query Layer (Live Connection)"])
        settings_layout.addWidget(self.layer_type_combo, 2, 1, 1, 2)
        
        query_layout.addLayout(settings_layout)
        query_layout.addStretch()
        query_tab.setLayout(query_layout)
        
        # Add a message bar and tabs to the main layout
        self.message_bar = QgsMessageBar()
        main_layout.addWidget(self.message_bar)
        tabs.addTab(connection_tab, "Connection")
        tabs.addTab(query_tab, "Query & Layer")
        main_layout.addWidget(tabs)
        
        # Buttons at the bottom
        button_layout = QHBoxLayout()
        
        load_btn = QPushButton("Load Layer")
        load_btn.clicked.connect(self.load_layer)
        button_layout.addWidget(load_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
    def on_connection_type_changed(self, text):
        """Handle connection type selection"""
        is_manual = text == "Manual Parameters"
        self.manual_conn_group.setVisible(is_manual)
        self.qgis_conn_group.setVisible(not is_manual)
        
    def refresh_qgis_connections(self):
        """Refresh list of QGIS named connections"""
        self.qgis_conn_combo.clear()
        try:
            from qgis.core import QgsProviderRegistry
            registry = QgsProviderRegistry.instance()
            metadata = registry.providerMetadata('mssql')
            if metadata:
                connections = metadata.connections(False)
                self.qgis_conn_combo.addItems(list(connections.keys()))
        except Exception as e:
            print(f"Error loading QGIS connections: {e}")
            
    def show_message(self, title, message, level=Qgis.MessageLevel.Info, duration=5):
        """Display a message in the dialog's message bar."""
        self.message_bar.clearWidgets()
        self.message_bar.pushMessage(title, message, level, duration)

    def test_connection(self):
        """Test the database connection"""
        try:
            if self.conn_type_combo.currentText() == "Manual Parameters":
                import pyodbc
                driver = self.driver_combo.currentText()
                server = self.server_input.text()
                database = self.database_input.text()
                username = self.username_input.text()
                password = self.password_input.text()
                
                conn_str = (
                    f"DRIVER={driver};"
                    f"SERVER={server};DATABASE={database};"
                    f"UID={username};PWD={password}"
                )
                
                conn = pyodbc.connect(conn_str)
                conn.close()
                
                self.show_message("Success", "Connection successful!", Qgis.MessageLevel.Success, 5)
            else:
                # Test QGIS connection
                from qgis.core import QgsProviderRegistry
                conn_name = self.qgis_conn_combo.currentText()
                registry = QgsProviderRegistry.instance()
                metadata = registry.providerMetadata('mssql')
                conn = metadata.findConnection(conn_name, False)
                
                if conn:
                    self.show_message("Success", "QGIS connection found!", Qgis.MessageLevel.Success, 5)
                else:
                    self.show_message("Error", "Connection not found!", Qgis.MessageLevel.Warning, 5)
                    
        except Exception as e:
            self.show_message("Connection Failed", f"Error: {str(e)}", Qgis.MessageLevel.Critical, 10)
            
    def select_crs(self):
        """Open CRS selection dialog"""
        dlg = QgsProjectionSelectionDialog()
        if dlg.exec():
            self.crs = dlg.crs().authid()
            self.crs_display.setText(self.crs)
            
    def load_layer(self):
        """Load the layer from SQL Server"""
        try:
            # Validate query
            query = self.query_editor.toPlainText().strip()
            if not query:
                self.show_message("Validation Error", "Please enter a SQL query", Qgis.MessageLevel.Warning, 5)
                return
                
            # Validate layer name
            layer_name = self.layer_name_input.text().strip()
            if not layer_name:
                self.show_message("Validation Error", "Please enter a layer name", Qgis.MessageLevel.Warning, 5)
                return
            
            # Get connection parameters
            if self.conn_type_combo.currentText() == "Manual Parameters":
                # For manual parameters, we need to create a loader that uses direct connection
                import pyodbc
                driver = self.driver_combo.currentText()
                server = self.server_input.text()
                database = self.database_input.text()
                username = self.username_input.text()
                password = self.password_input.text()
                
                conn_str = (
                    f"DRIVER={driver};"
                    f"SERVER={server};DATABASE={database};"
                    f"UID={username};PWD={password}"
                )
                
                # Test the connection first
                test_conn = pyodbc.connect(conn_str)
                test_conn.close()
                
                # Create a custom loader that uses direct connection
                loader = MSSQLLayerLoaderDirect(
                    conn_str=conn_str,
                    query=query,
                    geometry_type=self.geom_type_combo.currentText(),
                    crs=self.crs
                )
            else:
                # Use QGIS named connection
                conn_name = self.qgis_conn_combo.currentText()
                loader = MSSQLLayerLoader(
                    qgis_connection_name=conn_name,
                    query=query,
                    geometry_type=self.geom_type_combo.currentText(),
                    crs=self.crs
                )
            
            # Load the layer
            if self.layer_type_combo.currentText() == "Memory Layer (Static Snapshot)":
                loader.load_memory_layer(layer_name)
            else:
                loader.load_query_layer(layer_name)
                
            self.show_message("Success", f"Layer '{layer_name}' loaded successfully!", Qgis.MessageLevel.Success, 5)
            
        except Exception as e:
            print(traceback.format_exc())
            self.show_message("Error Loading Layer", str(e), Qgis.MessageLevel.Critical, 10)


class MSSQLLayerLoaderDirect(MSSQLLayerLoader):
    """Extended MSSQLLayerLoader that can use direct pyodbc connection strings"""
    
    def __init__(self, conn_str, query, geometry_type='Polygon', crs='EPSG:4326'):
        # Initialize parent without connection name (we'll override the connection method)
        super().__init__(qgis_connection_name=None, query=query, 
                         geometry_type=geometry_type, crs=crs)
        self.conn_str = conn_str
        
    def _get_connection_info(self):
        """Override to return the direct connection string"""
        return self.conn_str
    
    def connect(self):
        """Override to use direct connection string"""
        import pyodbc
        self.conn = pyodbc.connect(self.conn_str)
        self.cursor = self.conn.cursor()
        self.cursor.execute(self.query)
