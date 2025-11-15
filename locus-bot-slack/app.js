require("dotenv").config();
const { App } = require("@slack/bolt");
const { query } = require("@anthropic-ai/claude-agent-sdk");
const fs = require("fs");
const path = require("path");
const { getWalletId, getManagerId, getBudgetInfo } = require("./tools");

/**
 * Initializes Slack Bolt app with SocketMode
 */
const app = new App({
  token: process.env.SLACK_BOT_TOKEN,
  socketMode: true,
  appToken: process.env.SLACK_APP_TOKEN,
});

/**
 * Process OCR text with Claude and execute Locus payment
 */
async function processOcrAndPay(ocrText, say, thread_ts) {
  try {
    console.log("🤖 Processing OCR text with Claude Agent...\n");
    console.log("OCR Text:");
    console.log("─".repeat(50));
    console.log(ocrText);
    console.log("─".repeat(50));
    console.log("");

    // Post initial processing message in thread
    await say({
      text: "🤖 Analyzing payment request...",
      thread_ts: thread_ts,
    });

    // Configure MCP connection to Locus
    const mcpServers = {
      locus: {
        type: "http",
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
        "getWalletId",
        "getManagerId", 
        "getBudgetInfo",
      ],
      apiKey: process.env.ANTHROPIC_API_KEY,
      // Auto-approve Locus and custom tool usage
      canUseTool: async (toolName, input) => {
        if (toolName.startsWith("mcp__locus__")) {
          console.log(`🔧 Claude is using tool: ${toolName}`);
          console.log(`   Input:`, JSON.stringify(input, null, 2));
          return {
            behavior: "allow",
            updatedInput: input,
          };
        }
        
        // Handle custom tools
        if (["getWalletId", "getManagerId", "getBudgetInfo"].includes(toolName)) {
          console.log(`🔧 Claude is using custom tool: ${toolName}`);
          console.log(`   Input:`, JSON.stringify(input, null, 2));
          
          // Execute the custom tool and return the result
          let result;
          try {
            switch (toolName) {
              case "getWalletId":
                result = getWalletId(input.slackUserId);
                break;
              case "getManagerId":
                result = getManagerId(input.slackUserId);
                break;
              case "getBudgetInfo":
                result = getBudgetInfo(input.slackUserId);
                break;
            }
            
            return {
              behavior: "allow",
              updatedInput: input,
              result: result,
            };
          } catch (error) {
            return {
              behavior: "allow",
              updatedInput: input,
              result: `Error executing ${toolName}: ${error.message}`,
            };
          }
        }
        
        return {
          behavior: "deny",
          message: "Only Locus and custom tools are allowed",
        };
      },
    };

    // Load prompt template from file and substitute OCR text
    const promptTemplate = fs.readFileSync(path.join(__dirname, "prompt", "main.txt"), "utf8");
    const prompt = promptTemplate.replace("${ocrText}", ocrText);

    console.log("🎯 Sending to Claude with Locus tools access...\n");
    console.log("─".repeat(50));

    let mcpStatus = null;
    let finalResult = null;
    let toolCalls = [];

    for await (const message of query({
      prompt,
      options,
    })) {
      if (message.type === "system" && message.subtype === "init") {
        // Check MCP connection status
        const mcpServersInfo = message.mcp_servers;
        mcpStatus = mcpServersInfo?.find((s) => s.name === "locus");
        if (mcpStatus?.status === "connected") {
          console.log("✓ Connected to Locus MCP server\n");
        } else {
          console.warn("⚠️  MCP connection issue\n");
        }
      } else if (message.type === "assistant") {
        // Track tool usage from assistant messages
        const assistantMsg = message;
        if (assistantMsg.content) {
          for (const block of assistantMsg.content) {
            if (block.type === "tool_use") {
              toolCalls.push(block.name);
              console.log(`🔧 Tool called: ${block.name}`);

              // Post tool usage update in thread
              await say({
                text: `🔧 Processing payment with tool: ${block.name}`,
                thread_ts: thread_ts,
              });
            }
          }
        }
      } else if (message.type === "result" && message.subtype === "success") {
        finalResult = message.result;
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

    // Post final result in thread
    await say({
      text: `✅ Processing Complete!\n\n${finalResult}`,
      thread_ts: thread_ts,
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error("❌ Error processing OCR text:", errorMessage);

    // Post error in thread
    await say({
      text: `❌ Error processing payment: ${errorMessage}`,
      thread_ts: thread_ts,
    });

    throw error;
  }
}

/**
 * Listen for "PAYMENT REQUEST" keyword
 */
app.message("PAYMENT REQUEST", async ({ message, say }) => {
  try {
    console.log("\n" + "=".repeat(60));
    console.log("💰 Explicit payment request detected!");
    console.log("=".repeat(60) + "\n");

    // Echo back in thread
    await say({
      text: `📋 Processing your payment request:\n\n${message.text}`,
      thread_ts: message.ts,
    });

    // Process the payment
    await processOcrAndPay(message.text, say, message.ts);
  } catch (error) {
    console.error("Error handling payment request:", error);
    await say({
      text: `❌ Failed to process: ${error.message}`,
      thread_ts: message.ts,
    });
  }
});

/**
 * Health check - respond to "ping"
 */
app.message("ping", async ({ message, say }) => {
  await say({
    text: ":white_check_mark: Pong! Locus Payment Bot is online and ready!",
    thread_ts: message.ts,
  });
});

/**
 * Start the app
 */
(async () => {
  try {
    await app.start(process.env.PORT || 3000);
    console.log("⚡️ Locus Payment Bot is running!");
    console.log("🎯 Listening for payment requests...");
    console.log("📱 Monitoring keywords: INVOICE, RECEIPT, PAYMENT REQUEST");
  } catch (error) {
    console.error("Failed to start app:", error);
    process.exit(1);
  }
})();
