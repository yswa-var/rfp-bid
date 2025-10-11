import os
import sys
import traceback
import logging
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import (
    BotFrameworkAdapter,
    BotFrameworkAdapterSettings,
    ConversationState,
    MemoryStorage,
    UserState,
)
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.schema import Activity, ActivityTypes

from bot import DOCXAgentBot
from config import DefaultConfig

# Configure structured logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('teams_bot.log', mode='a', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# Create adapter
SETTINGS = BotFrameworkAdapterSettings(
    DefaultConfig.APP_ID,
    DefaultConfig.APP_PASSWORD,
    DefaultConfig.APP_TYPE,
    DefaultConfig.APP_TENANTID
)
ADAPTER = BotFrameworkAdapter(SETTINGS)

MEMORY = MemoryStorage()
CONVERSATION_STATE = ConversationState(MEMORY)
USER_STATE = UserState(MEMORY)

# Create the Bot
BOT = DOCXAgentBot(CONVERSATION_STATE, USER_STATE)

# Catch-all for errors
async def on_error(context, error):
    # Enhanced error logging with detailed context
    activity = context.activity
    logger.error("=== BOT ERROR OCCURRED ===")
    logger.error(f"Error Type: {type(error).__name__}")
    logger.error(f"Error Message: {str(error)}")

    # Log activity context if available
    if activity:
        logger.error(f"Activity Type: {activity.type}")
        logger.error(f"Activity ID: {activity.id}")
        logger.error(f"Channel ID: {activity.channel_id}")
        logger.error(f"Conversation ID: {activity.conversation.id}")
        logger.error(f"From User: {activity.from_property.name} ({activity.from_property.id})")

        if hasattr(activity, 'text') and activity.text:
            logger.error(f"Message Text: {activity.text[:200]}{'...' if len(activity.text) > 200 else ''}")

        if hasattr(activity, 'attachments') and activity.attachments:
            logger.error(f"Attachments Count: {len(activity.attachments)}")
            for i, attachment in enumerate(activity.attachments):
                logger.error(f"  Attachment {i}: {attachment.content_type}")

    # Log full traceback
    logger.error("Full Traceback:")
    logger.error(traceback.format_exc())

    # Send user-friendly error message
    await context.send_activity("The bot encountered an error or bug.")
    await context.send_activity(
        "To continue to run this bot, please fix the bot source code."
    )

    # Send detailed trace for emulator debugging
    if context.activity and context.activity.channel_id == "emulator":
        trace_activity = Activity(
            label="TurnError",
            name="on_turn_error Trace",
            timestamp=datetime.utcnow(),
            type=ActivityTypes.trace,
            value=f"{type(error).__name__}: {str(error)}",
            value_type="https://www.botframework.com/schemas/error",
        )
        await context.send_activity(trace_activity)

    # Clear conversation state to prevent error persistence
    try:
        # Get property accessors for both conversation and user state
        conv_state_accessor = CONVERSATION_STATE.create_property("ConversationData")
        user_state_accessor = USER_STATE.create_property("UserData")

        # Clear the state data by setting to empty dict and saving
        await conv_state_accessor.set(context, {})
        await user_state_accessor.set(context, {})

        # Save the cleared state
        await CONVERSATION_STATE.save_changes(context)
        await USER_STATE.save_changes(context)

        logger.info("Successfully cleared conversation and user state after error")
    except Exception as cleanup_error:
        logger.error(f"Failed to cleanup state after error: {cleanup_error}")
        logger.error(f"Cleanup error details: {traceback.format_exc()}")

    logger.error("=== ERROR HANDLING COMPLETED ===")

ADAPTER.on_turn_error = on_error

async def messages(req: Request) -> Response:
    """Handle incoming bot messages with comprehensive debugging"""
    request_id = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{id(req)}"

    # Log incoming request details
    logger.info(f"=== INCOMING REQUEST [{request_id}] ===")
    logger.info(f"Method: {req.method}")
    logger.info(f"Path: {req.path}")
    logger.info(f"Remote: {req.remote}")
    logger.info(f"Content-Type: {req.headers.get('Content-Type', 'Not provided')}")

    # Log sanitized headers (excluding sensitive auth data)
    sanitized_headers = {}
    for key, value in req.headers.items():
        if key.lower() not in ['authorization', 'x-ms-token-aad-id-token']:
            sanitized_headers[key] = value
        else:
            sanitized_headers[key] = f"[{key}]: Bearer [REDACTED]"

    logger.info(f"Headers: {sanitized_headers}")

    # Validate content type
    content_type = req.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        logger.warning(f"Unsupported content type: {content_type}")
        return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    try:
        # Parse request body
        body = await req.json()
        logger.info(f"Request Body Size: {len(str(body))} characters")

        # Deserialize activity for processing
        activity = Activity().deserialize(body)

        # Log activity details (safely)
        logger.info(f"Activity Type: {activity.type}")
        logger.info(f"Activity ID: {activity.id}")
        logger.info(f"Channel: {activity.channel_id}")
        logger.info(f"Conversation: {activity.conversation.id}")
        logger.info(f"From User: {activity.from_property.name} ({activity.from_property.id})")

        # Log message text if present (truncated for security)
        if hasattr(activity, 'text') and activity.text:
            text = activity.text
            logger.info(f"Message Text: {text[:100]}{'...' if len(text) > 100 else ''}")

        # Log attachments if present
        if hasattr(activity, 'attachments') and activity.attachments:
            logger.info(f"Attachments Count: {len(activity.attachments)}")
            for i, attachment in enumerate(activity.attachments):
                logger.info(f"  Attachment {i}: {attachment.content_type}")

    except Exception as parse_error:
        logger.error(f"Failed to parse request body or deserialize activity: {parse_error}")
        logger.error(f"Parse error details: {traceback.format_exc()}")
        return Response(status=HTTPStatus.BAD_REQUEST)

    # Extract auth header
    auth_header = req.headers.get("Authorization", "")
    if auth_header:
        logger.info(f"Authentication: Bearer token provided (length: {len(auth_header)})")
    else:
        logger.warning("No Authorization header provided")

    # Process activity through Bot Framework
    logger.info("Processing activity through BotFramework adapter...")
    try:
        response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)

        # Log response details
        if response:
            logger.info(f"Response Status: {response.status}")
            logger.info(f"Response Body Type: {type(response.body)}")

            if hasattr(response.body, '__len__') and response.body:
                logger.info(f"Response Body Size: {len(str(response.body))} characters")
            elif response.body:
                logger.info(f"Response Body: {response.body}")

            logger.info(f"=== REQUEST COMPLETED [{request_id}] ===")
            return json_response(data=response.body, status=response.status)
        else:
            logger.info("No response generated by bot handler")
            logger.info(f"=== REQUEST COMPLETED [{request_id}] ===")
            return Response(status=HTTPStatus.OK)

    except Exception as processing_error:
        logger.error(f"Error processing activity: {processing_error}")
        logger.error(f"Activity details: {traceback.format_exc()}")
        logger.error(f"=== REQUEST FAILED [{request_id}] ===")
        raise

# Health check endpoint
async def health_check(req: Request) -> Response:
    """Health check with basic system status logging"""
    logger.info("=== HEALTH CHECK ===")
    logger.info(f"Health check requested from: {req.remote}")

    # Basic system status
    status_info = {
        "status": "healthy",
        "service": "docx-agent-teams-bot",
        "timestamp": datetime.utcnow().isoformat(),
        "bot_configured": BOT is not None,
        "adapter_configured": ADAPTER is not None,
        "memory_available": MEMORY is not None
    }

    logger.info(f"Health Status: {status_info}")
    return json_response(status_info)

def init_func(argv):
    """Initialize the web application with comprehensive logging"""
    logger.info("=== INITIALIZING TEAMS BOT APPLICATION ===")

    APP = web.Application(middlewares=[aiohttp_error_middleware])
    APP.router.add_post("/api/messages", messages)
    APP.router.add_get("/health", health_check)

    logger.info(f"Routes configured: /api/messages (POST), /health (GET)")
    logger.info(f"Bot Framework Adapter configured: {ADAPTER is not None}")
    logger.info(f"Bot instance created: {BOT is not None}")

    # Log configuration status
    config_status = {
        "app_id": bool(DefaultConfig.APP_ID),
        "app_password": bool(DefaultConfig.APP_PASSWORD),
        "port": DefaultConfig.PORT,
        "backend_url": DefaultConfig.BACKEND_API_URL
    }
    logger.info(f"Configuration status: {config_status}")

    return APP

if __name__ == "__main__":
    logger.info("=== STARTING TEAMS BOT SERVER ===")

    APP = init_func(None)

    try:
        logger.info(f"Starting server on 0.0.0.0:{DefaultConfig.PORT}")
        logger.info("Bot server is ready to receive requests")

        web.run_app(APP, host="0.0.0.0", port=DefaultConfig.PORT)

    except Exception as error:
        logger.error(f"Failed to start server: {error}")
        logger.error(f"Startup error details: {traceback.format_exc()}")
        raise error
      
