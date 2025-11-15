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
        system_prompt = """You are a professional reimbursement manager helping employees submit expense reports. 

Your primary responsibilities:
1. Request and collect receipt images from users for their expense reimbursement requests
2. Review submitted receipts (even if they appear as placeholder data for now)
3. Extract and verify key information from receipts:
   - Date of purchase
   - Merchant/vendor name
   - Total amount
   - Itemized expenses (if available)
   - Payment method
   - Business purpose/category
4. Identify any missing or unclear information
5. Request additional details when needed (e.g., business purpose, approval code, project code)
6. Provide clear, friendly guidance throughout the reimbursement process
7. Confirm when all required information is collected

Communication style:
- Be professional, friendly, and helpful
- Use clear, concise language
- Ask one question at a time when requesting information
- Acknowledge receipt submissions promptly
- Explain what information you found and what might be missing

When processing a receipt (even with dummy data), you should:
- Summarize the key information you "found"
- Point out any fields that appear missing or unclear
- Ask specific follow-up questions if needed
- Confirm the reimbursement amount before finalizing

Remember: Your goal is to make the reimbursement process smooth and efficient for employees."""

        self.options.system = system_prompt
        self.agent = ClaudeSDKClient(self.options)
        
    def has_image_content(self, message: UserMessage = None, user_input: str = None) -> bool:
        """
        Check if the user message contains image content.
        Returns True if an image is detected, False otherwise.
        
        This checks both:
        1. Actual image blocks in the message (if the SDK supports it)
        2. Text indicators that the user is mentioning an image/receipt
        """
        # Check for actual image blocks in message content
        if message:
            if hasattr(message, 'content') and message.content:
                # Check all blocks in the message content
                for block in message.content:
                    # Check if block has image-related attributes
                    # The SDK might use different block types for images
                    block_type = type(block).__name__.lower()
                    if 'image' in block_type:
                        return True
                    # Also check if block has image data attributes
                    if hasattr(block, 'source'):
                        source = block.source
                        if hasattr(source, 'type') and 'image' in str(source.type).lower():
                            return True
                    if hasattr(block, 'type') and 'image' in str(block.type).lower():
                        return True
        
        # Check text input for image/receipt indicators
        if user_input:
            user_lower = user_input.lower()
            image_keywords = [
                'receipt', 'image', 'photo', 'picture', 'scan', 
                'attached', 'upload', 'here is', 'here\'s', 'i have a receipt',
                'submitting', 'submitted', 'sending', 'sent'
            ]
            if any(keyword in user_lower for keyword in image_keywords):
                return True
                
        return False
    
    def create_dummy_receipt_data(self) -> dict:
        """
        Create dummy receipt data as a placeholder for actual image processing.
        In a real implementation, this would be replaced with actual OCR/vision processing.
        """
        return {
            "merchant": "Sample Coffee Shop",
            "date": "2024-01-15",
            "total_amount": 24.50,
            "currency": "USD",
            "items": [
                {"description": "Coffee", "amount": 5.50},
                {"description": "Sandwich", "amount": 12.00},
                {"description": "Tax", "amount": 1.75},
                {"description": "Tip", "amount": 5.25}
            ],
            "payment_method": "Credit Card",
            "missing_info": [
                "business_purpose",
                "project_code"
            ],
            "confidence": "medium"  # Some fields may need verification
        }
    
    async def process_message(self, user_input: str = None, user_message: UserMessage = None):
        """
        Process a user message, detect images, and handle the reimbursement workflow.
        """
        # Detect if this is an image message
        has_image = self.has_image_content(message=user_message, user_input=user_input)
        
        # If image detected, create dummy receipt data and inform the agent
        if has_image:
            print("\n[System: Receipt image detected. Processing...]")
            dummy_data = self.create_dummy_receipt_data()
            
            # Create a context message for the agent about the processed receipt
            # This simulates what would come from OCR/vision processing
            receipt_summary = f"""The user has submitted a receipt image. I've processed it and extracted the following information:

RECEIPT DETAILS:
- Merchant/Vendor: {dummy_data['merchant']}
- Purchase Date: {dummy_data['date']}
- Total Amount: ${dummy_data['total_amount']:.2f} {dummy_data['currency']}
- Payment Method: {dummy_data['payment_method']}

ITEMIZED EXPENSES:
"""
            for item in dummy_data['items']:
                receipt_summary += f"  • {item['description']}: ${item['amount']:.2f}\n"
            
            receipt_summary += f"\n⚠️ MISSING INFORMATION REQUIRED: {', '.join(dummy_data['missing_info'])}\n"
            receipt_summary += f"Processing Confidence: {dummy_data['confidence']}\n\n"
            receipt_summary += "Please acknowledge receipt of this information, summarize what you found, and request the missing details from the user in a friendly, professional manner."
            
            # Send the receipt processing result to the agent
            await self.agent.query(receipt_summary)
            return
            
        # Query with user input if provided (normal text conversation)
        if user_input:
            await self.agent.query(user_input)
    
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

