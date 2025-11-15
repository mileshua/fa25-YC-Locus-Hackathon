import os
import aiohttp
import logging
import asyncio
from pathlib import Path
from slack_bolt import App
import json
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
import time
import math
from session_manager import SessionManager

manager = SessionManager()

# Configure logging to display in terminal
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# This sample slack application uses SocketMode
# For the companion getting started setup guide, 
# see: https://slack.dev/bolt-python/tutorial/getting-started 

# Initializes your app with your bot token
app = AsyncApp(token=os.environ.get("SLACK_BOT_TOKEN"))
app.sessions = {}

# Respond to ping messages
@app.message("ping")
async def handle_ping_message(message, say):
    """Respond to 'ping' messages"""
    await say("Pong")


async def download_files(user_id, files, client, logger):
    """
    Download files from Slack to local downloads directory using aiohttp.
    
    Args:
        user_id: User ID to prefix file names
        files: List of file info dictionaries from Slack event
        client: Slack WebClient instance
        logger: Logger instance
        
    Returns:
        List of successfully downloaded file names
    """
    # Create downloads directory if it doesn't exist
    downloads_dir = Path("downloads")
    downloads_dir.mkdir(exist_ok=True)

    # Download each file
    downloaded_files = []
    headers = {"Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN')}"}
    
    async with aiohttp.ClientSession() as session:
        for file_info in files:
            file_id = file_info.get("id")
            file_name = user_id + "_" + file_info.get("name", f"file_{file_id}")
            
            try:
                # Get file info and download URL
                file_response = await client.files_info(file=file_id)
                file_data = file_response["file"]
                
                # Get the private download URL
                url_private = file_data.get("url_private")
                
                if url_private:
                    # Download the file asynchronously
                    async with session.get(url_private, headers=headers) as response:
                        response.raise_for_status()
                        
                        # Save the file
                        file_path = downloads_dir / file_name
                        with open(file_path, "wb") as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        
                        downloaded_files.append(file_name)
                        logger.info(f"Downloaded file: {file_name} to {file_path}")
                else:
                    logger.warning(f"No download URL found for file {file_id}")
                    
            except Exception as e:
                logger.error(f"Error downloading file {file_id}: {str(e)}")
    
    return downloaded_files


async def handle_session_content(user_id, message_content, downloaded_file_names, logger):
    sessions = manager.get_sessions()
    print("sessions: " + str(sessions))
    session = sessions.get(user_id)
    if not session or session.get("start_time", math.inf) - time.perf_counter() > 300: # 5 minutes
        print("no session found")
        if session:
            manager.delete_session(user_id)
        manager.create_session(user_id, time.perf_counter())
    else:
        print("session found")
        print("session: " + str(session))

    return await manager.new_dm_message(user_id, message_content, downloaded_file_names)
    


@app.event("message")
async def handle_dms(event, say, logger, client):
    channel_type = event.get("channel_type")
    if channel_type != "im":
        return
    
    # Set thinking status
    channel = event.get("channel")
    thread_ts = event.get("thread_ts") or event.get("ts")  # Use message timestamp as thread_ts for DMs
    try:
        await client.assistant_threads_setStatus(
            channel_id=channel,
            thread_ts=thread_ts,
            status="thinking...",
            loading_messages=[
                "Teaching the hamsters to type faster…",
                "Untangling the internet cables…",
                "Consulting the office goldfish…",
                "Polishing up the response just for you…",
                "Convincing the AI to stop overthinking…",
            ],
        )
    except Exception as e:
        logger.warning(f"Failed to set thinking status: {str(e)}")
    
    # Only handle file_share subtype (file uploads)
    downloaded_file_names = []
    user_id = event.get("user")

    subtype = event.get("subtype")
    if subtype == "file_share":
        files = event.get("files", [])
        logger.info(f"Received DM file upload from {user_id}: {files}")
        downloaded_file_names = await download_files(user_id, files, client, logger)
        print("downloaded_file_names: " + str(downloaded_file_names))

    message_text = event.get("text", "")
    responses = await handle_session_content(user_id, message_text, downloaded_file_names, logger)
    try:
        if isinstance(responses, list):
            for response in responses:
                if response and response.get("location") == "dm":
                    await say(response.get("content"))
                elif response and response.get("location") == "request":
                    await client.chat_postMessage(
                        channel="C09T45YDXAA",
                        text=response.get("content"),
                    )
        else:
            response = responses
            if response and response.get("location") == "dm":
                await say(response.get("content"))
            elif response and response.get("location") == "request":
                await client.chat_postMessage(
                    channel="C09T45YDXAA",
                    text=response.get("content"),
                )
    except Exception as e:
        logger.warning(f"Failed to send response: {str(e)}")
    
    # Clear thinking status after processing is complete
    try:
        await client.assistant_threads_setStatus(
            channel_id=channel,
            thread_ts=thread_ts,
            status="",
        )
    except Exception as e:
        logger.warning(f"Failed to clear thinking status: {str(e)}")


# Start your app
async def main():
    handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    await handler.start_async()

if __name__ == "__main__":
    asyncio.run(main())
