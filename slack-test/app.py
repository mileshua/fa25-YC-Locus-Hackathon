import os
import requests
import logging
from pathlib import Path
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import time
import math
from ocr import extract_text
from session_manager import SessionManager

client = SessionManager()

# Configure logging to display in terminal
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# This sample slack application uses SocketMode
# For the companion getting started setup guide, 
# see: https://slack.dev/bolt-python/tutorial/getting-started 

# Initializes your app with your bot token
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
app.sessions = {}

# Respond to ping messages
@app.message("ping")
def handle_ping_message(message, say):
    """Respond to 'ping' messages"""
    say("Pong")


def download_files(user_id, files, client, logger):
    """
    Download files from Slack to local downloads directory.
    
    Args:
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
    for file_info in files:
        file_id = file_info.get("id")
        file_name = user_id + "_" + file_info.get("name", f"file_{file_id}")
        
        try:
            # Get file info and download URL
            file_response = client.files_info(file=file_id)
            file_data = file_response["file"]
            
            # Get the private download URL
            url_private = file_data.get("url_private")
            
            if url_private:
                # Download the file
                headers = {"Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN')}"}
                response = requests.get(url_private, headers=headers, stream=True)
                response.raise_for_status()
                
                # Save the file
                file_path = downloads_dir / file_name
                with open(file_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                downloaded_files.append(file_name)
                logger.info(f"Downloaded file: {file_name} to {file_path}")
            else:
                logger.warning(f"No download URL found for file {file_id}")
                
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {str(e)}")
    
    return downloaded_files


def handle_session_content(user_id, message_content, downloaded_file_names, logger):
    sessions = client.get_sessions()
    print("sessions: " + str(sessions))
    session = sessions.get(user_id)
    if not session or session.get("start_time", math.inf) - time.perf_counter() > 300: # 5 minutes
        print("no session found")
        if session:
            client.delete_session(user_id)
        client.create_session(user_id, time.perf_counter())
    else:
        print("session found")
        print("session: " + str(session))

    return client.new_dm_message(user_id, message_content, downloaded_file_names)
    


@app.event("message")
def handle_dms(event, say, logger, client):
    subtype = event.get("subtype")
    channel_type = event.get("channel_type")

    if channel_type != "im":
        return
    
    # Only handle file_share subtype (file uploads)
    downloaded_file_names = []
    message_text = event.get("text", "")
    user_id = event.get("user")
    if subtype == "file_share":

        # Only acknowledge files that are sent via DM (im)
        user = event.get("user")
        files = event.get("files", [])

        logger.info(f"Received DM file upload from {user}: {files}")

        # Download files
        downloaded_file_names = download_files(user_id, files, client, logger)

        # Acknowledge the upload
        if downloaded_file_names:
            files_list = ", ".join(downloaded_file_names)

            # Acknowledge the upload
            if len(downloaded_file_names) > 0:
                for file_name in downloaded_file_names:
                    obj = extract_text(Path("downloads") / file_name)
                    if obj["is_receipt"]:
                        if obj["too_blurry"]:
                            say("The receipt is too blurry to read. Please send a clearer image.")
                        else:
                            say(f"Receipt detected! Here's the information: {obj}")
                    else:
                        say("This is not a receipt.")
            else:
                say("Thanks for sending the file! I encountered an error downloading it. 📁")
                logger.info(f"Sent notification to #reinbursements channel for files: {files_list}")
        else:
            say("Thanks for sending the file! I encountered an error downloading it. 📁")
    
    response = handle_session_content(user_id, message_text, downloaded_file_names, logger)

    if response and response.get("location") == "dm":
        say(response.get("content"))


# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
