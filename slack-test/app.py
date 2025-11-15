import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# This sample slack application uses SocketMode
# For the companion getting started setup guide, 
# see: https://slack.dev/bolt-python/tutorial/getting-started 

# Initializes your app with your bot token
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

@app.event("message")
def handle_file_uploads(event, say, logger):
    subtype = event.get("subtype")
    
    # Only handle file_share subtype (file uploads)
    if subtype == "file_share":
        channel_type = event.get("channel_type")

        # Only acknowledge files that are sent via DM (im)
        if channel_type == "im":
            user = event.get("user")
            files = event.get("files", [])

            logger.info(f"Received DM file upload from {user}: {files}")

            # Acknowledge the upload
            say("Thanks for sending the file! I've received it. 📁")

# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
