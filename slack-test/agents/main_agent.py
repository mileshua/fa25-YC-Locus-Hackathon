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

        self.valid_receipt = False

    def extract_recipt_data(self, downloaded_file_names: list):
        # Acknowledge the upload
        valid = False
        if len(downloaded_file_names) > 0:
            for file_name in downloaded_file_names:
                obj = extract_text(Path("downloads") / file_name)
                if obj["is_receipt"]:
                    if obj["too_blurry"]:
                        return valid, "The receipt is too blurry to read. Please send a clearer image."
                    else:
                        valid = True
                        return valid, f"Receipt detected! Here's the information: {obj}"
                else:
                    return valid, "This is not a receipt."
        else:
            return valid, "Thanks for sending the file! I encountered an error downloading it. 📁"
        
    async def process_user_message(self, message_content: str, downloaded_file_names: list):
        """
        Process a user message, detect images, and handle the reimbursement workflow.
        """
        
        if self.valid_receipt == False:
            if downloaded_file_names:
                self.valid_receipt, message = self.extract_recipt_data(downloaded_file_names)
                async with self.agent:
                    await self.agent.query(f"Receipt is valid: {self.valid_receipt}. " + message)
                if self.valid_receipt:
                    return {"location": "dm", "content": message}
                else:
                    return {"location": "dm", "content": message}
            else:
                return {"location": "dm", "content": "No files uploaded. Please upload a receipt image."}
        else:
            return {"location": "dm", "content": "No more receipt images needed at this time."}
        #await self.agent.query(receipt_summary)
    
    async def chat(self):
        """
        Main chat loop for interacting with the reimbursement manager.
        """
        print("=" * 60)
        print("💼 REIMBURSEMENT MANAGER")
        print("=" * 60)
        print("Hello! I'm here to help you with your expense reimbursement.")
        print("Please start by describing your expense or uploading a receipt image.")
        print("Type 'quit' or 'exit' to end the conversation.\n")
        
        async with self.agent:
            while True:
                try:
                    # Get user input
                    user_input = input("\nYou: ").strip()
                    
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        print("\nThank you for using the reimbursement service. Have a great day!")
                        break
                    
                    if not user_input:
                        continue
                    
                    # Process the message (this will detect images and handle them)
                    await self.process_message(user_input=user_input)
                    
                    # Receive and display responses from the agent
                    print("\nReimbursement Manager: ", end="", flush=True)
                    async for message in self.agent.receive_response():
                        if isinstance(message, AssistantMessage):
                            for block in message.content:
                                if isinstance(block, TextBlock):
                                    print(block.text, end="", flush=True)
                            print()  # New line after message
                        elif isinstance(message, ResultMessage):
                            # Handle result messages if needed
                            pass
                            
                except KeyboardInterrupt:
                    print("\n\nConversation interrupted. Goodbye!")
                    break
                except Exception as e:
                    print(f"\nError: {e}")
                    print("Please try again or type 'quit' to exit.")

async def main():
    """Main entry point for the reimbursement manager."""
    manager = ReimbursementManager()
    await manager.chat()

if __name__ == "__main__":
    asyncio.run(main())

