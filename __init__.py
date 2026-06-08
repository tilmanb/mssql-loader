def classFactory(iface):
    from .mssql_loader_plugin import MSSQLLoaderPlugin
    return MSSQLLoaderPlugin(iface)
