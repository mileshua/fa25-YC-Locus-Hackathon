require("dotenv").config();
const { App } = require("@slack/bolt");
const { query } = require("@anthropic-ai/claude-agent-sdk");
const fs = require("fs");
const path = require("path");
/*const { 
  initializeTools, 
  customMCP
} = require("./tools");*/

/**
 * Initializes Slack Bolt app with SocketMode
 */
const app = new App({
  token: process.env.SLACK_BOT_TOKEN,
  socketMode: true,
  appToken: process.env.SLACK_APP_TOKEN,
});

// Initialize tools with app instance for DM functionality
/*initializeTools(app);*/

async function* generateMessages(prompt) {
  yield {
    type: "user",
    message: {
      role: "user",
      content: prompt
    }
  };
}

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
      /*custom_tools: customMCP*/
    };

    const options = {
      mcpServers,
      // Use both allowedTools and disallowedTools for reliable blocking (workaround for SDK bugs)
      allowedTools: [
        "mcp__locus__*", // Allow all Locus tools
        "mcp__list_resources",
        "mcp__read_resource",
        //"mcp__custom_tools__*"
      ],
      permissionMode: "default", // Use default permission mode for controlled execution
      apiKey: process.env.ANTHROPIC_API_KEY,
      // Enhanced canUseTool for permission checking only
      canUseTool: async (toolName, input) => {
        console.log(`🔧 Tool: ${toolName}`);
        console.log(`📥 Input: ${JSON.stringify(input, null, 2)}`);
        
        // Allow Locus MCP tools
        if (toolName.startsWith("mcp__locus__")) {
          console.log(`✅ Allowing Locus tool: ${toolName}`);
          return {
            behavior: "allow",
            updatedInput: input,
          };
        }
        
        // Allow custom tools (execution handled by onToolUse)
        /*if (toolName.startsWith("mcp__custom_tools__")) {
          console.log(`✅ Allowing custom tool: ${toolName}`);
          return {
            behavior: "allow",
            updatedInput: input,
          };
        }*/
        
        // Deny all other tools
        console.log(`🚫 Denying unknown tool: ${toolName}`);
        return {
          behavior: "deny",
          message: `Tool ${toolName} is not in the allowed list. Only Locus and custom payment tools are permitted.`,
        };
      },
    };

    console.log("🎯 Sending to Claude with Locus tools access...\n");
    console.log("─".repeat(50));

    let mcpStatus = null;
    let finalResult = null;
    let toolCalls = [];

    // Load prompt template from file and substitute OCR text
    const promptTemplate = fs.readFileSync(path.join(__dirname, "prompt", "main.txt"), "utf8");
    const walletData = fs.readFileSync(path.join(__dirname, "wallet.json"), "utf8");
    const budgetData = fs.readFileSync(path.join(__dirname, "budget.json"), "utf8");
    const hierarchyData = fs.readFileSync(path.join(__dirname, "hierarchy.json"), "utf8");
    const prompt = promptTemplate.replace("${ocrText}", ocrText).replace("${walletData}", walletData).replace("${budgetData}", budgetData).replace("${hierarchyData}", hierarchyData);

    for await (const message of query({
      prompt: generateMessages(prompt),
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
