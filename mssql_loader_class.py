from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsDataSourceUri,
    QgsFields,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsProviderRegistry,
    Qgis
)
from PyQt5.QtCore import QVariant
import pyodbc


class MSSQLLayerLoader:
    def __init__(self, qgis_connection_name, query, geometry_type='Polygon', crs='EPSG:4326', message_callback=None):
        """Initialize the MSSQLLayerLoader.

        Args:
            qgis_connection_name (str): Name of the MSSQL connection stored in QGIS.
            query (str): SQL query to fetch rows including a geometry column.
            geometry_type (str): Geometry type to use when creating layers (default 'Polygon').
            crs (str): Coordinate reference system string (default 'EPSG:4326').
            message_callback (callable, optional): Function to show UI messages.
                Expected signature: (title, message, level, duration).
        """

        self.connection_name = qgis_connection_name
        self.query = query
        self.geometry_type = geometry_type
        self.crs = crs
        self.message_callback = message_callback

        self.conn = None
        self.cursor = None
        self.columns = []
        self.types = []
        self.geom_col_index = None
        self.fields = QgsFields()
        self.field_indexes = []

    def _get_connection_info(self):
        """Build and return a pyodbc connection string from a QGIS MSSQL connection.

        The method reads the connection metadata stored in QGIS for the
        provider 'mssql', parses it and returns a DSN string suitable for
        passing to `pyodbc.connect()`.

        Returns:
            str: A pyodbc-style connection string (DRIVER/UID/PWD/etc.).

        Raises:
            Exception: if the named connection is not found in QGIS.
        """
        # Get connection string from QGIS
        uri = QgsProviderRegistry.instance().providerMetadata('mssql').findConnection(self.connection_name, False)
        if uri is None:
            raise Exception(f"Connection '{self.connection_name}' not found in QGIS")

        # Build pyodbc connection string
        #params = uri.connectionInfo(True).split(';')
        params = uri.uri().replace("'","").split(" ")
        conn_dict = dict(param.split('=', 1) for param in params if '=' in param)

        driver = '{SQL Server}'
        server = conn_dict.get('host', '')
        database = conn_dict.get('dbname', '')
        username = conn_dict.get('user', '')
        password = conn_dict.get('password', '')

        conn_str = (
            f"DRIVER={driver};"
            f"SERVER={server};DATABASE={database};"
            f"UID={username};PWD={password}"
        )

        return conn_str

    def connect(self):
        """Open a database connection and execute the configured query.

        After calling this method `self.conn` will be a live pyodbc connection
        and `self.cursor` will have executed `self.query` so results can be
        inspected or iterated.
        """

        conn_str = self._get_connection_info()
        self.conn = pyodbc.connect(conn_str)
        self.cursor = self.conn.cursor()
        self.cursor.execute(self.query)

    def _detect_geometry_column(self):
        """Detect which column in the query result contains geometry.

        The detection strategy attempts to find a binary/blob column that looks
        like geometry by checking SQL types and sample data length. If that
        fails it falls back to looking for a column named 'geom' (case
        insensitive). When found, `self.geom_col_index` is set and `self.columns`
        and `self.types` are populated.

        Raises:
            Exception: if no geometry column can be detected.
        """

        self.columns = [col[0] for col in self.cursor.description]
        self.types = [col[1] for col in self.cursor.description]
        sample_row = self.cursor.fetchone()

        for i, (col_type, value) in enumerate(zip(self.types, sample_row)):
            if col_type in (pyodbc.SQL_BINARY, pyodbc.SQL_VARBINARY, pyodbc.SQL_LONGVARBINARY):
                if value is not None and len(value) > 16:
                    self.geom_col_index = i
                    break
        
        if self.geom_col_index is None:
            matches = [i for i, v in enumerate(self.columns) if v.lower() == 'geom']
            if matches:
                self.geom_col_index = matches[0]
            else:
                raise Exception("No geometry column detected!")

        self.cursor.execute(self.query)  # Reset cursor

    def _map_sql_to_qvariant(self, sql_type):
        """Map a pyodbc SQL type to a PyQt `QVariant` type for QGIS fields.

        Args:
            sql_type: The type code from `cursor.description` for a column.

        Returns:
            QVariant type constant suitable for `QgsField`.
        """

        if sql_type in (pyodbc.SQL_INTEGER, pyodbc.SQL_SMALLINT, pyodbc.SQL_TINYINT):
            return QVariant.Int
        elif sql_type in (pyodbc.SQL_BIGINT,):
            return QVariant.LongLong
        elif sql_type in (pyodbc.SQL_FLOAT, pyodbc.SQL_REAL, pyodbc.SQL_DOUBLE):
            return QVariant.Double
        elif sql_type in (pyodbc.SQL_TYPE_DATE, pyodbc.SQL_TYPE_TIMESTAMP, pyodbc.SQL_TYPE_TIME):
            return QVariant.DateTime
        else:
            return QVariant.String

    def _create_qgsfields(self):
        """Populate `self.fields` and `self.field_indexes` from query metadata.

        For each column returned by the query (except the detected geometry
        column) this method maps the SQL type to a `QVariant` and appends a
        corresponding `QgsField` to `self.fields`. The numeric indexes of non-
        geometry columns are stored in `self.field_indexes` to assist when
        building feature attributes.
        """

        for i, (name, sql_type) in enumerate(zip(self.columns, self.types)):
            if i != self.geom_col_index:
                qvar_type = self._map_sql_to_qvariant(sql_type)
                self.fields.append(QgsField(name, qvar_type))
                self.field_indexes.append(i)

    def _create_memory_layer(self, layer_name='SQL Server memory layer'):
        """Create and add a memory `QgsVectorLayer` populated from the cursor.

        The memory layer is a static snapshot: features are read from the
        currently-executed cursor and added to an in-memory layer which is
        then added to the current `QgsProject`.

        Args:
            layer_name (str): Display name for the created memory layer.
        """
        # Create a memory layer from the query results (snapshot of data at creation)
        layer = QgsVectorLayer(f"{self.geometry_type}?crs={self.crs}", layer_name, "memory")
        provider = layer.dataProvider()
        provider.addAttributes(self.fields)
        layer.updateFields()

        for row in self.cursor.fetchall():
            feature = QgsFeature()
            feature.setFields(self.fields)
            feature.setAttributes([row[i] for i in self.field_indexes])
            geom_wkb = row[self.geom_col_index]
            if geom_wkb:
                _g = QgsGeometry()
                _g.fromWkb(bytes(geom_wkb))
                feature.setGeometry(_g)
            provider.addFeature(feature)

        layer.updateExtents()
        QgsProject.instance().addMapLayer(layer)

    def _show_message(self, title, message, level=Qgis.MessageLevel.Info, duration=5):
        if self.message_callback:
            self.message_callback(title, message, level, duration)

    def _create_query_layer(self, layer_name='SQL Server query layer'):
        """Create and add a live QGIS query layer backed by the SQL query.

        This method builds a `QgsDataSourceUri` that wraps the loader's SQL
        query as a derived table and creates a `QgsVectorLayer` using the
        'mssql' provider. The resulting layer will re-run the query when QGIS
        needs to refresh its features.

        Args:
            layer_name (str): Display name for the created query layer.
        """
        # Build the URI for the QGIS query layer (live query layer)
        uri = QgsDataSourceUri()
        conn_info = self._get_connection_info()
        self._show_message("Connection Info", str(conn_info), Qgis.MessageLevel.Info, 5)
    
        #uri.setConnection(conn_info['server'], conn_info['database'], conn_info['username'], conn_info['password'])
        #uri.setConnection('localhost', 'til1', 'sa', '12345678!A')
        uri.setHost("localhost")
        uri.setDatabase('til1')
        uri.setDriver('SQL Server')
        uri.setUsername('sa')
        uri.setPassword('30419!30419H')
        uri.setParam('disableInvalidGeometryHandling','0')
        uri.setParam('type','Point')
        uri.setUseEstimatedMetadata(False)
        uri.setDataSource('', f"({self.query})", 'geom')  # Treat the query as a derived table
        #uri.setDataSource('', f'neueTabelle', 'geom')  # Treat the query as a derived table
        #uri.setDataSource('', f"({self.query})", self.geometry_type)  # Treat the query as a derived table
        
        # Add CRS
        uri.setSrid("25832")
        
        self._show_message("Query URI", uri.uri(), Qgis.MessageLevel.Info, 5)

        # Create the QgsVectorLayer using the query
        layer = QgsVectorLayer(uri.uri(), layer_name, "mssql")
        
        
        if not layer.isValid():
            raise Exception("Failed to create the query layer.")

        QgsProject.instance().addMapLayer(layer)

    def load_memory_layer(self, layer_name='SQL Server memory layer'):
        """Creates a memory layer with a snapshot of the data"""
        self.connect()
        self._detect_geometry_column()
        self._create_qgsfields()
        self._create_memory_layer(layer_name)  # Create the memory layer (static)
        self.cursor.close()
        self.conn.close()

    def load_query_layer(self, layer_name='SQL Server query layer'):
        """Creates a live query layer that will re-query the database on each redraw"""
        self.connect()
        self._detect_geometry_column()
        self._create_qgsfields()
        self._create_query_layer(layer_name)  # Create the live query layer
        self.cursor.close()
        self.conn.close()
