# MSSQL Loader for QGIS

![MSSQL Loader Icon](icon.png)

A PyQT5-based QGIS plugin for loading spatial data from Microsoft SQL Server database SQL queries directly into QGIS.

This is mostly vibe-coded using Github Copilot.

## Features

- **Dual Connection Modes**: 
  - Manual parameters entry (direct connection via pyodbc)
  - QGIS named connections (use existing QGIS connection settings)
- **Query Builder**: Write custom SQL queries with geometry support
- **Two Layer Types**:
  - **Memory Layer**: Static snapshot of query results at load time
  - **Query Layer**: Live connection that re-queries on each redraw
- **Flexible Geometry**: Support for Point, LineString, Polygon, and Multi* variants
- **CRS Selection**: Choose any supported coordinate reference system
- **Connection Testing**: Verify database connectivity before loading
- **Automatic Geometry Detection**: Auto-detects geometry column from query results

## Installation

1. Locate your QGIS plugins directory:
   - Windows: `C:\Users\[UserName]\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins`
   - macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins`
   - Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins`

2. Copy the `mssql-loader` folder into your plugins directory

3. Restart QGIS

4. Enable the plugin in Plugins → Manage and Install Plugins → Search for "MSSQL Loader"

## Requirements

- QGIS 3.0 or later
- Python 3.6+
- `pyodbc` package (`pip install pyodbc`)
- SQL Server ODBC Driver (native or ODBC Driver 17 for SQL Server)

## Usage

### Basic Workflow

1. **Open the Plugin**: Navigate to `Database → MSSQL Loader` in the menu

2. **Configure Connection** (Connection Tab):
   - Choose connection type:
     - **Manual Parameters**: Enter server, database, username, password
     - **QGIS Named Connection**: Select from your existing QGIS connections
   - Click "Test Connection" to verify connectivity

3. **Define Query** (Query & Layer Tab):
   - Write your SQL query in the editor
   - Ensure the geometry column is named `geom` or it will be auto-detected
   - Configure:
     - Layer Name
     - Geometry Type (Point, LineString, Polygon, etc.)
     - CRS (click "Select CRS" for options)
     - Layer Type (Memory or Query Layer)

4. **Load**: Click "Load Layer" to add the data to your project

### Query Requirements

- **Geometry Column**: Must be in WKB (Well-Known Binary) format or a native SQL geometry
- **Column Naming**: Geometry column should be named `geom` or contain "geom" in the name for auto-detection
- **Aliases**: Use descriptive aliases for columns: `SELECT id, name, geom.STAsBinary() AS geom FROM table`

### Example Queries

```sql
-- Basic query with geometry
SELECT id, name, geom FROM my_database.dbo.spatial_table

-- With filtering
SELECT id, description, geom 
FROM my_database.dbo.boundaries 
WHERE category = 'administrative'

-- Converting SQL geometry to WKB
SELECT id, name, geometry.STAsBinary() AS geom 
FROM my_database.dbo.points
```

## Layer Types Explained

### Memory Layer (Static Snapshot)
- Data is loaded once from the database into QGIS memory
- Fast for visualization
- Data does not update if database changes
- Best for: Stable reference data, smaller datasets

### Query Layer (Live Connection)

**this does not work at the moment**

- Maintains a live connection to the database
- Query is re-executed on each map redraw
- Reflects real-time database changes
- Slower for large datasets
- Best for: Real-time data monitoring, frequently updated tables

## Troubleshooting

### "No geometry column detected"
- Ensure your query includes a geometry column
- Check that geometry is named `geom` or try explicitly naming it: `SELECT ..., geometry AS geom`
- Verify geometry is in WKB format (`select geom.STAsBinary() as geom, ...`)

### "Connection failed"
- Verify server name and port
- Check username/password credentials
- Ensure SQL Server is running and accessible
- Confirm firewall isn't blocking the connection
- Try the connection with a different ODBC driver

### "QGIS connection not found"
- In QGIS, configure a named connection: `Data → Add Layer → New Generic Database Connection`
- Set provider to "MSSQL"
- Test the connection in QGIS before using with this plugin

### Performance Issues
- For large datasets, filter your query to reduce record count
- Use Memory Layer for one-time loads
- Add spatial indexes on geometry columns in SQL Server

## Architecture

The plugin consists of:

- **mssql_loader_class.py**: Core loader class handling database connections and layer creation
- **mssql_loader_dialog.py**: PyQT5 dialog UI for parameter configuration
- **mssql_loader_plugin.py**: Main plugin class integrating with QGIS
- **__init__.py**: Plugin factory function

## License

GPL v2

## Support

For issues, questions, or feature requests, please refer to the main project repository.
