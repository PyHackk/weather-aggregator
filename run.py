# run.py
"""Application entry point."""
from app import create_app

app = create_app('development')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    
    
    
    
    
    
    
    
    
    
    
          # Trino External (for tables and cc apps)
      - TRINO_EXT_HOST=trino.qdi.dev.echonet
      - TRINO_EXT_PORT=443
      - TRINO_EXT_USER=SVC2AUXCMPPCIA0
      - TRINO_EXT_AUTH_USER=SVC2AUXCMPPCIA0
      - TRINO_EXT_AUTH_PASSWORD=YOUR_PASSWORD_HERE
      - TRINO_EXT_CATALOG=hive
      - TRINO_EXT_HTTP_SCHEME=https




TRINO_CONFIG = {
    'host': os.environ.get('TRINO_EXT_HOST', 'trino.qdi.dev.echonet'),
    'port': int(os.environ.get('TRINO_EXT_PORT', 443)),
    'user': os.environ.get('TRINO_EXT_USER', 'SVC2AUXCMPPCIA0'),
    'catalog': os.environ.get('TRINO_EXT_CATALOG', 'hive'),
    'schema': 'silver',
    'http_scheme': os.environ.get('TRINO_EXT_HTTP_SCHEME', 'https'),
    'verify': False,
    'auth_user': os.environ.get('TRINO_EXT_AUTH_USER', 'SVC2AUXCMPPCIA0'),
    'auth_password': os.environ.get('TRINO_EXT_AUTH_PASSWORD', ''),
}







        self.config = {
            "host": os.environ.get('TRINO_EXT_HOST', 'trino.qdi.dev.echonet'),
            "port": int(os.environ.get('TRINO_EXT_PORT', 443)),
            "user": os.environ.get('TRINO_EXT_USER', 'SVC2AUXCMPPCIA0'),
            "catalog": os.environ.get('TRINO_EXT_CATALOG', 'hive'),
            "schema": "gold",
            "http_scheme": os.environ.get('TRINO_EXT_HTTP_SCHEME', 'https'),
            "verify": False,
        }

    