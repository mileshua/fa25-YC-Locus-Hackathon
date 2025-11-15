import asyncio
import os
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
from ocr import extract_text

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
        system_prompt = open("prompts/user_interactions.txt", "r").read()

        self.options.system = system_prompt
        self.agent = ClaudeSDKClient(self.options)
        
    async def process_user_message(self, message_content: str, downloaded_file_names: list):
        """
        Process a user message, detect images, and handle the reimbursement workflow.
        """

        receipt_detected = False
        blurry = False

        # Acknowledge the upload
        if downloaded_file_names:
            files_list = ", ".join(downloaded_file_names)

            # Acknowledge the upload
            if len(downloaded_file_names) > 0:
                for file_name in downloaded_file_names:
                    obj = extract_text(Path("downloads") / file_name)
                    if obj["is_receipt"]:
                        if obj["too_blurry"]:
                            receipt_detected = True
                            blurry = True
                            return {"location": "dm", "content": "The receipt is too blurry to read. Please send a clearer image."}
                        else:
                            receipt_detected = True
                            blurry = True
                            return {"location": "dm", "content": f"Receipt detected! Here's the information: {obj}"}
                    else:
                        receipt_detected = True
                        blurry = True
                        return {"location": "dm", "content": "This is not a receipt."}
            else:
                return {"location": "dm", "content": "Thanks for sending the file! I encountered an error downloading it. 📁"}
        
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

