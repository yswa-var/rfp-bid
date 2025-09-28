"""
Enhanced Teams App with full RFP system integration
"""

import sys
from pathlib import Path
from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.schema import Activity

from config import Config
from bot import RFPBot
from rfp_bridge import RFPSystemBridge

SETTINGS = BotFrameworkAdapterSettings(Config.APP_ID, Config.APP_PASSWORD)
ADAPTER = BotFrameworkAdapter(SETTINGS)

BOT = RFPBot()
BRIDGE = RFPSystemBridge()

async def init_app():
    """Initialize the application"""
    try:

        if BRIDGE.test_integration():
            print("✅ RFP system integration successful")
        else:
            print("⚠️ RFP system integration test failed")
        
        await BOT.on_startup()
        print("✅ Teams bot initialized")
        
    except Exception as e:
        print(f"❌ App initialization failed: {e}")

async def messages(req: Request) -> Response:
    """Handle incoming messages"""
    if "application/json" in req.headers["Content-Type"]:
        body = await req.json()
    else:
        return Response(status=415)

    activity = Activity().deserialize(body)
    auth_header = req.headers["Authorization"] if "Authorization" in req.headers else ""

    try:
        response = await ADAPTER.process_activity(activity, auth_header, BOT.on_message_activity)
        if response:
            return json_response(data=response.body, status=response.status)
        return Response(status=201)
    except Exception as e:
        print(f"Error processing activity: {e}")
        return Response(status=500)

async def health_check(req: Request) -> Response:
    """Health check endpoint"""
    try:
        system_info = BRIDGE.get_system_info()
        return json_response({
            "status": "healthy",
            "system_info": system_info
        })
    except Exception as e:
        return json_response({
            "status": "error", 
            "error": str(e)
        }, status=500)

def create_app() -> web.Application:
    """Create the web application"""
    app = web.Application(middlewares=[aiohttp_error_middleware])
    app.router.add_post("/api/messages", messages)
    app.router.add_get("/health", health_check)
    
    app.on_startup.append(lambda app: init_app())
    
    return app

if __name__ == "__main__":
    APP = create_app()
    try:
        web.run_app(APP, host="0.0.0.0", port=Config.PORT)
    except Exception as error:
        raise error