import os
import requests
from pathlib import Path
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from ocr import extract_text

# This sample slack application uses SocketMode
# For the companion getting started setup guide, 
# see: https://slack.dev/bolt-python/tutorial/getting-started 

# Initializes your app with your bot token
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

@app.event("message")
def handle_file_uploads(event, say, logger, client):
    subtype = event.get("subtype")
    
    # Only handle file_share subtype (file uploads)
    if subtype == "file_share":
        channel_type = event.get("channel_type")

        # Only acknowledge files that are sent via DM (im)
        if channel_type == "im":
            user = event.get("user")
            files = event.get("files", [])

            logger.info(f"Received DM file upload from {user}: {files}")

            # Create downloads directory if it doesn't exist
            downloads_dir = Path("downloads")
            downloads_dir.mkdir(exist_ok=True)

            # Download each file
            downloaded_files = []
            for file_info in files:
                file_id = file_info.get("id")
                file_name = file_info.get("name", f"file_{file_id}")
                
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

            # Acknowledge the upload
            if len(downloaded_files) > 0:
                for file_name in downloaded_files:
                    obj = extract_text(downloads_dir / file_name)
                    if obj["is_receipt"]:
                        say(f"Receipt detected! Here's the information: {obj}")
                    else:
                        say("This is not a receipt.")
            else:
                say("Thanks for sending the file! I encountered an error downloading it. 📁")

# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
