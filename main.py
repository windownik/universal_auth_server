import os

import uvicorn
from fastapi.openapi.utils import get_openapi

from lib.sql_connect import app


ip_server = os.environ.get("IP_SERVER")
ip_port = os.environ.get("PORT_SERVER")

ip_port = 10020 if ip_port is None else ip_port
ip_server = "127.0.0.1" if ip_server is None else ip_server


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Welcome to Universal auth API",
        version="0.5",
        description="This is main API page",
        routes=app.routes,
        tags=[
            {'name': 'Auth', 'description': "Auth user methods in server"},
            {'name': 'Devices', 'description': "Device management"},
        ]
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

if __name__ == '__main__':
    uvicorn.run('main:app', reload=True)
