import asyncio
import os
import warnings
from dotenv import load_dotenv
from claude_agent_sdk import (
    ClaudeAgentOptions, 
    ClaudeSDKClient, 
    AssistantMessage, 
    TextBlock, 
    ResultMessage,
    UserMessage
)
from pathlib import Path
from agents.ocr import extract_text

# Suppress ResourceWarnings from anyio streams in claude-agent-sdk
# These are internal to the SDK and are cleaned up during garbage collection
warnings.filterwarnings("ignore", category=ResourceWarning, module="anyio")

# Load environment variables from .env file
load_dotenv()

class ReimbursementManager:
    """
    An AI agent that acts as a reimbursement manager.
    Handles receipt submissions, validates information, and processes reimbursement requests.
    """
    
    def __init__(self):
        self.options = ClaudeAgentOptions()
        self.options.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.options.temperature = 0.7  # Slightly higher for more natural conversation
        self.options.max_tokens = 2000  # Increased for detailed responses
        self.options.top_p = 1
        self.options.frequency_penalty = 0
        
        # Set system prompt for the reimbursement manager role
        prompt_path = Path("prompts/user_interactions.txt")
        with prompt_path.open("r", encoding="utf-8") as f:
            system_prompt = f.read()

        self.options.system_prompt = system_prompt
        self.agent = ClaudeSDKClient(self.options)

        self.conversation_history = ""

        self.valid_receipt = False
        self.all_info_collected = False

    def extract_recipt_data(self, downloaded_file_names: list):
        # Acknowledge the upload
        valid = False
        if len(downloaded_file_names) > 0:
            for file_name in downloaded_file_names:
                obj = extract_text(Path("downloads") / file_name)
                if obj["is_receipt"]:
                    if obj["too_blurry"]:
                        return valid, "The receipt is too blurry to read! Please take a clearer image."
                    else:
                        valid = True
                        return valid, f"Receipt detected! Here's the information: {obj}"
                else:
                    return valid, "This is not a receipt! I can only process reinbursement requests for receipts."
        else:
            return valid, "Thanks for sending the file! Unfortunately i encountered an error downloading it. 📁"
        
    async def process_user_message(self, message_content: str, downloaded_file_names: list):
        """
        Process a user message, detect images, and handle the reimbursement workflow.
        """
        
        if not self.valid_receipt:
            if downloaded_file_names:
                self.valid_receipt, message = self.extract_recipt_data(downloaded_file_names)
                async with self.agent:
                    prompt = f"Receipt is valid: {self.valid_receipt}."
                    if self.valid_receipt:
                        prompt += "Here is the receipt info. Remember this and remember that a valid receipt has been provided. Move onto Phase 2 next. Also infer any context and information possible from the provided receipt info:  " + message
                    await self.agent.query(self.conversation_history + prompt)
                    self.conversation_history += ("\n" + prompt)
                if self.valid_receipt:
                    async with self.agent:
                        self.conversation_history += ("\n" +"A valid receipt has been provided. Now ask the user about any more info you need that isn't on the receipt. Do not regurgitate receipt details unless you are asked to.")
                        await self.agent.query(self.conversation_history)
                        async for message in self.agent.receive_response():
                            if isinstance(message, AssistantMessage):
                                for block in message.content:
                                    if isinstance(block, TextBlock):
                                        self.more_info = block.text
                                        self.conversation_history += ("\n" + self.more_info)
                                        return False, {"location": "dm", "content": self.more_info}
                else:
                    return False, {"location": "dm", "content": message}
            else:
                return False, {"location": "dm", "content": "To start a reinbursement request, please upload a receipt image!"}
        else:

            if self.valid_receipt and downloaded_file_names:
                return False, {"location": "dm", "content": "A valid receipt has already been provided! If you would like to reinburse a new receipt, please make a new request."}
            if self.all_info_collected:
                return True, {"location": "dm", "content": "All necessary information collected! I'll let you know if anything else is needed and if the request is approved!"}
            async with self.agent:
                all_info_message = " If all necessary information has been found, simply say 'done'"
                await self.agent.query(self.conversation_history + message_content + all_info_message)
                self.conversation_history += ("\n" + message_content + all_info_message)
                async for message in self.agent.receive_response():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                self.more_info = block.text
                                self.conversation_history += ("\n" + self.more_info)
                                if "done" in self.more_info.lower():
                                    self.all_info_collected = True
                                    return True, [{"location" : "request", "content" : "Yo wsg chat :)"},
                                        {"location" : "dm", "content" : "Perfect! All necessary info has been collected! I'll get back to you once there's an update on the status of your request :)"}]
                                return False, {"location": "dm", "content": self.more_info}
