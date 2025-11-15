import "dotenv/config";
import { query } from "@anthropic-ai/claude-agent-sdk";
import { WebClient } from "@slack/web-api";

// Initialize Slack client
const slackClient = new WebClient(process.env.SLACK_BOT_TOKEN);

interface OcrMessage {
  text: string;
  channelId: string;
  timestamp: string;
  user: string;
}

/**
 * Fetch messages from a Slack channel that contain OCR text
 */
async function fetchOcrMessagesFromSlack(
  channelId: string,
  limit: number = 10
): Promise<OcrMessage[]> {
  try {
    console.log(`📱 Fetching messages from Slack channel: ${channelId}`);

    const result = await slackClient.conversations.history({
      channel: channelId,
      limit: limit,
    });

    if (!result.messages) {
      console.log("No messages found in channel");
      return [];
    }

    // Filter messages that contain text (OCR results)
    const ocrMessages: OcrMessage[] = result.messages
      .filter((msg) => msg.text && msg.text.trim().length > 0)
      .map((msg) => ({
        text: msg.text || "",
        channelId: channelId,
        timestamp: msg.ts || "",
        user: msg.user || "unknown",
      }));

    console.log(`✓ Found ${ocrMessages.length} messages with text\n`);
    return ocrMessages;
  } catch (error) {
    console.error("Error fetching Slack messages:", error);
    throw error;
  }
}

/**
 * Process OCR text with Claude and execute Locus payment
 */
async function processOcrAndPay(ocrText: string): Promise<void> {
  try {
    console.log("🤖 Processing OCR text with Claude Agent...\n");
    console.log("OCR Text:");
    console.log("─".repeat(50));
    console.log(ocrText);
    console.log("─".repeat(50));
    console.log("");

    // Configure MCP connection to Locus
    const mcpServers = {
      locus: {
        type: "http" as const,
        url: "https://mcp.paywithlocus.com/mcp",
        headers: {
          Authorization: `Bearer ${process.env.LOCUS_API_KEY}`,
        },
      },
    };

    const options = {
      mcpServers,
      allowedTools: [
        "mcp__locus__*", // Allow all Locus tools
        "mcp__list_resources",
        "mcp__read_resource",
      ],
      apiKey: process.env.ANTHROPIC_API_KEY,
      // Auto-approve Locus tool usage
      canUseTool: async (toolName: string, input: Record<string, unknown>) => {
        if (toolName.startsWith("mcp__locus__")) {
          console.log(`🔧 Claude is using tool: ${toolName}`);
          console.log(`   Input:`, JSON.stringify(input, null, 2));
          return {
            behavior: "allow" as const,
            updatedInput: input,
          };
        }
        return {
          behavior: "deny" as const,
          message: "Only Locus tools are allowed",
        };
      },
    };

    // Create a prompt that asks Claude to extract payment info and execute payment
    const prompt = `You are an automated payment processing assistant. I have received the following text from an OCR scan of a receipt or invoice:

${ocrText}

Please analyze this text and:
1. Extract any payment-related information (amount, recipient, description, etc.)
2. If you find a payment request with clear amount and recipient information, AUTOMATICALLY use the Locus tools to process the payment immediately
3. If the information is unclear or incomplete, explain what's missing

You are authorized to process payments automatically. Do not ask for confirmation - just process valid payment requests immediately using the Locus payment tools.`;

    console.log("🎯 Sending to Claude with Locus tools access...\n");
    console.log("─".repeat(50));

    let mcpStatus: any = null;
    let finalResult: any = null;
    let toolCalls: string[] = [];

    for await (const message of query({
      prompt,
      options,
    })) {
      if (message.type === "system" && message.subtype === "init") {
        // Check MCP connection status
        const mcpServersInfo = (message as any).mcp_servers;
        mcpStatus = mcpServersInfo?.find((s: any) => s.name === "locus");
        if (mcpStatus?.status === "connected") {
          console.log("✓ Connected to Locus MCP server\n");
        } else {
          console.warn("⚠️  MCP connection issue\n");
        }
      } else if (message.type === "assistant") {
        // Track tool usage from assistant messages
        const assistantMsg = message as any;
        if (assistantMsg.content) {
          for (const block of assistantMsg.content) {
            if (block.type === "tool_use") {
              toolCalls.push(block.name);
              console.log(`🔧 Tool called: ${block.name}`);
            }
          }
        }
      } else if (message.type === "result" && message.subtype === "success") {
        finalResult = (message as any).result;
      }
    }

    console.log("─".repeat(50));
    console.log("\n📊 Processing Results:\n");

    if (toolCalls.length > 0) {
      console.log("🔧 Tools Used:");
      toolCalls.forEach((tool, idx) => {
        console.log(`   ${idx + 1}. ${tool}`);
      });
      console.log("");
    }

    console.log("💬 Claude Response:");
    console.log(finalResult);
    console.log("\n✓ Processing completed!\n");
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error("❌ Error processing OCR text:", errorMessage);
    throw error;
  }
}

/**
 * Monitor Slack channel and process OCR messages
 */
async function monitorSlackChannel(channelId: string): Promise<void> {
  console.log("🎯 Starting Locus Slack OCR Payment Bot...\n");
  console.log(`👀 Monitoring Slack channel: ${channelId}\n`);

  try {
    // Fetch recent messages from Slack
    const ocrMessages = await fetchOcrMessagesFromSlack(channelId, 5);

    if (ocrMessages.length === 0) {
      console.log("No OCR messages to process.");
      return;
    }

    // Process each message
    for (const [index, message] of ocrMessages.entries()) {
      console.log(`\n${"=".repeat(60)}`);
      console.log(`Processing message ${index + 1} of ${ocrMessages.length}`);
      console.log(`${"=".repeat(60)}\n`);

      await processOcrAndPay(message.text);

      // Add delay between processing messages to avoid rate limits
      if (index < ocrMessages.length - 1) {
        console.log("⏳ Waiting before processing next message...\n");
        await new Promise((resolve) => setTimeout(resolve, 2000));
      }
    }

    console.log("\n✅ All messages processed successfully!");
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error("❌ Error:", errorMessage);
    console.error("\nPlease check:");
    console.error("  • Your .env file contains valid credentials");
    console.error("  • SLACK_BOT_TOKEN is set and valid");
    console.error("  • SLACK_CHANNEL_ID is correct");
    console.error("  • Your Locus and Anthropic API keys are correct");
    console.error("  • The bot has access to the Slack channel\n");
    throw error;
  }
}

async function main(): Promise<void> {
  const channelId = process.env.SLACK_CHANNEL_ID;

  if (!channelId) {
    console.error("❌ SLACK_CHANNEL_ID environment variable is required");
    console.error("\nAdd this to your .env file:");
    console.error("SLACK_CHANNEL_ID=your-channel-id\n");
    process.exit(1);
  }

  if (!process.env.SLACK_BOT_TOKEN) {
    console.error("❌ SLACK_BOT_TOKEN environment variable is required");
    console.error("\nAdd this to your .env file:");
    console.error("SLACK_BOT_TOKEN=xoxb-your-token\n");
    process.exit(1);
  }

  await monitorSlackChannel(channelId);
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});

// Create confirmation where the user confirms
