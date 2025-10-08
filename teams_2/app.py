"""
Teams Bot Web Server with LangGraph Integration
"""
import sys
import logging
from datetime import datetime
from http import HTTPStatus
from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import (
    BotFrameworkAdapter,
    BotFrameworkAdapterSettings,
)
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.schema import Activity

from config import Config
from bot import LangGraphTeamsBot
from thread_manager import ThreadManager

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Config.LOG_FILE, mode='a', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# Validate configuration
try:
    Config.validate()
    logger.info("Configuration validated successfully")
except Exception as e:
    logger.error(f"Configuration validation failed: {e}")
    sys.exit(1)

# Create Bot Framework Adapter
SETTINGS = BotFrameworkAdapterSettings(
    Config.APP_ID,
    Config.APP_PASSWORD,
    Config.APP_TYPE,
    Config.APP_TENANTID
)
ADAPTER = BotFrameworkAdapter(SETTINGS)

# Initialize thread manager
THREAD_MANAGER = ThreadManager(Config.THREAD_MAPPINGS_FILE)

# Create bot
BOT = LangGraphTeamsBot(Config, THREAD_MANAGER)

# Error handler for adapter
async def on_error(context, error):
    """Handle errors from Bot Framework"""
    logger.error(f"=== BOT ERROR ===")
    logger.error(f"Error: {error}", exc_info=True)
    
    activity = context.activity
    if activity:
        logger.error(f"Activity Type: {activity.type}")
        logger.error(f"Activity ID: {activity.id}")
        logger.error(f"Conversation: {activity.conversation.id}")
    
    # Send user-friendly error message
    await context.send_activity(
        "❌ An error occurred. Please try again or contact support if the issue persists."
    )
    
    logger.error(f"=== ERROR HANDLING COMPLETED ===")

ADAPTER.on_turn_error = on_error


async def messages(req: Request) -> Response:
    """Handle incoming messages from Teams"""
    request_id = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{id(req)}"
    
    logger.info(f"=== INCOMING REQUEST [{request_id}] ===")
    logger.info(f"Method: {req.method}")
    logger.info(f"Path: {req.path}")
    logger.info(f"Remote: {req.remote}")
    
    # Validate content type
    content_type = req.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        logger.warning(f"Unsupported content type: {content_type}")
        return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
    
    try:
        # Parse request body
        body = await req.json()
        activity = Activity().deserialize(body)
        
        logger.info(f"Activity Type: {activity.type}")
        logger.info(f"Conversation: {activity.conversation.id}")
        
        if hasattr(activity, 'text') and activity.text:
            logger.info(f"Message: {activity.text[:100]}")
        
        # Extract auth header
        auth_header = req.headers.get("Authorization", "")
        
        # Process activity
        logger.info("Processing activity...")
        response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
        
        if response:
            logger.info(f"Response status: {response.status}")
            logger.info(f"=== REQUEST COMPLETED [{request_id}] ===")
            return json_response(data=response.body, status=response.status)
        else:
            logger.info(f"=== REQUEST COMPLETED [{request_id}] ===")
            return Response(status=HTTPStatus.OK)
    
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        logger.error(f"=== REQUEST FAILED [{request_id}] ===")
        return Response(status=HTTPStatus.INTERNAL_SERVER_ERROR)


async def health_check(req: Request) -> Response:
    """Health check endpoint"""
    logger.debug("Health check requested")
    
    try:
        # Basic health status
        status = {
            "status": "healthy",
            "service": "langgraph-teams-bot",
            "timestamp": datetime.utcnow().isoformat(),
            "langgraph_server": Config.LANGGRAPH_SERVER_URL,
            "assistant_id": Config.ASSISTANT_ID
        }
        
        # Try to ping LangGraph server
        try:
            assistants = await BOT.langgraph_client.assistants.search()
            status["langgraph_connection"] = "ok"
            status["assistants_count"] = len(assistants)
        except Exception as e:
            logger.warning(f"Could not connect to LangGraph server: {e}")
            status["langgraph_connection"] = "error"
            status["langgraph_error"] = str(e)
        
        return json_response(status)
    
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return json_response(
            {"status": "unhealthy", "error": str(e)},
            status=HTTPStatus.INTERNAL_SERVER_ERROR
        )


async def debug_threads(req: Request) -> Response:
    """Debug endpoint to view thread mappings"""
    logger.info("Debug threads endpoint called")
    
    try:
        mappings = await THREAD_MANAGER.get_all_mappings()
        
        return json_response({
            "count": len(mappings),
            "mappings": mappings
        })
    
    except Exception as e:
        logger.error(f"Debug endpoint error: {e}", exc_info=True)
        return json_response(
            {"error": str(e)},
            status=HTTPStatus.INTERNAL_SERVER_ERROR
        )


def init_app() -> web.Application:
    """Initialize the web application"""
    logger.info("=== INITIALIZING TEAMS BOT ===")
    
    app = web.Application(middlewares=[aiohttp_error_middleware])
    
    # Add routes
    app.router.add_post("/api/messages", messages)
    app.router.add_get("/health", health_check)
    app.router.add_get("/debug/threads", debug_threads)
    
    logger.info("Routes configured:")
    logger.info("  POST /api/messages - Teams messaging endpoint")
    logger.info("  GET  /health - Health check")
    logger.info("  GET  /debug/threads - Thread mappings debug")
    
    logger.info(f"LangGraph Server: {Config.LANGGRAPH_SERVER_URL}")
    logger.info(f"Assistant ID: {Config.ASSISTANT_ID}")
    logger.info(f"Bot configured: {BOT is not None}")
    
    return app


if __name__ == "__main__":
    logger.info("=== STARTING TEAMS BOT SERVER ===")
    
    app = init_app()
    
    try:
        logger.info(f"Starting server on {Config.HOST}:{Config.PORT}")
        logger.info("Bot server is ready to receive requests")
        
        web.run_app(app, host=Config.HOST, port=Config.PORT)
    
    except Exception as error:
        logger.error(f"Failed to start server: {error}", exc_info=True)
        sys.exit(1)

