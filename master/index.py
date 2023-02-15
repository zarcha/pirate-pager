from waitress import serve
from jproperties import Properties
import app

configs = Properties()
with open('server.properties', 'rb') as config_file:
    configs.load(config_file)

serve(app.app, host="0.0.0.0", port=configs.get("port").data)