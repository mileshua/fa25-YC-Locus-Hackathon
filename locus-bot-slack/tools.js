const fs = require("fs");
const path = require("path");
const { tool, createSdkMcpServer } = require("@anthropic-ai/claude-agent-sdk");
const { z } = require("zod");

console.log("Zod version:", require("zod/package.json").version);

// Store reference to Slack app for DM functionality
let slackApp = null;

function initializeTools(app) {
  slackApp = app;
}

// Tool definition for Claude Agent SDK
const getWalletId = tool(
  "getWalletId",
  "Get wallet ID for a given Slack user ID",
  z.object({
    slackUserId: z.string().describe("The Slack user ID to look up"),
  }),
  async (args, extra) => {
    console.log(`Input: ${JSON.stringify(args)}`);
    console.log(`Extra: ${JSON.stringify(extra)}`);
    return getWalletIdImpl(args);
  }
);

// Tool implementation function
async function getWalletIdImpl(input) {
  console.log(`Input: ${JSON.stringify(input)}`);
  const walletPath = path.join(__dirname, "wallet.json");

  if (!fs.existsSync(walletPath)) {
    console.log("wallet.json file not found. Please ensure the wallet mapping file exists.");
    throw new Error(
      "wallet.json file not found. Please ensure the wallet mapping file exists."
    );
  }

  const walletData = JSON.parse(fs.readFileSync(walletPath, "utf8"));

  if (!walletData[input.slackUserId]) {
    console.log(`No wallet ID found for Slack user ${input.slackUserId}. User may not be registered in the wallet system.`);
    throw new Error(
      `No wallet ID found for Slack user ${input.slackUserId}. User may not be registered in the wallet system.`
    );
  }

  console.log(`Found wallet ID for Slack user ${input.slackUserId}: ${walletData[input.slackUserId]}`);
  return { content: [{ type: "text", text: walletData[input.slackUserId] }] };
}

const getManagerId = tool(
  "getManagerId",
  "Get manager ID for a given Slack user ID. Returns empty string if no manager.",
  z.object({
    slackUserId: z.string().describe("The Slack user ID to look up"),
  }),
  async (args, extra) => {
    console.log(`Input: ${JSON.stringify(args)}`);
    console.log(`Extra: ${JSON.stringify(extra)}`);
    return getManagerIdImpl(args);
  }
);

async function getManagerIdImpl(input) {
  console.log(`Input: ${JSON.stringify(input)}`);
  const hierarchyPath = path.join(__dirname, "hierarchy.json");

  if (!fs.existsSync(hierarchyPath)) {
    console.log("hierarchy.json file not found. Please ensure the hierarchy mapping file exists.");
    throw new Error(
      "hierarchy.json file not found. Please ensure the hierarchy mapping file exists."
    );
  }

  const hierarchyData = JSON.parse(fs.readFileSync(hierarchyPath, "utf8"));

  if (!hierarchyData.hasOwnProperty(input.slackUserId)) {
    console.log(`No hierarchy information found for Slack user ${input.slackUserId}. User may not be registered in the hierarchy system.`);
    throw new Error(
      `No hierarchy information found for Slack user ${input.slackUserId}. User may not be registered in the hierarchy system.`
    );
  }

  console.log(`Found manager ID for Slack user ${input.slackUserId}: ${hierarchyData[input.slackUserId]}`);
  return { content: [{ type: "text", text: hierarchyData[input.slackUserId] }] };
}

const getBudgetInfo = tool(
  "getBudgetInfo",
  "Get budget information for a given Slack user ID, including total budget and dollars spent",
  z.object({
    slackUserId: z.string().describe("The Slack user ID to look up"),
  }),
  async (args, extra) => {
    console.log(`Input: ${JSON.stringify(args)}`);
    console.log(`Extra: ${JSON.stringify(extra)}`);
    return getBudgetInfoImpl(args);
  }
);

async function getBudgetInfoImpl(input) {
  console.log(`Input: ${JSON.stringify(input)}`);
  const budgetPath = path.join(__dirname, "budget.json");

  if (!fs.existsSync(budgetPath)) {
    console.log("budget.json file not found. Please ensure the budget mapping file exists.");
    throw new Error(
      "budget.json file not found. Please ensure the budget mapping file exists."
    );
  }

  const budgetData = JSON.parse(fs.readFileSync(budgetPath, "utf8"));

  if (!budgetData.hasOwnProperty(input.slackUserId)) {
    console.log(`No budget information found for Slack user ${input.slackUserId}. User may not be registered in the budget system.`);
    throw new Error(
      `No budget information found for Slack user ${input.slackUserId}. User may not be registered in the budget system.`
    );
  }

  console.log(`Found budget information for Slack user ${input.slackUserId}: ${budgetData[input.slackUserId]}`);
  return { content: [{ type: "text", text: budgetData[input.slackUserId] }] };
}

const sendDM = tool(
  "sendDM",
  "Send a direct message to a Slack user",
  z.object({
    slackUserId: z.string().describe("The Slack user ID to send message to"),
    message: z.string().describe("The message to send"),
  }),
  async (args, extra) => {
    console.log(`Input: ${JSON.stringify(args)}`);
    console.log(`Extra: ${JSON.stringify(extra)}`);
    return sendDMImpl(args);
  }
);

async function sendDMImpl(input) {
  console.log(`Input: ${JSON.stringify(input)}`);
  if (!slackApp) {
    console.log("Slack app not initialized. Call initializeTools() first.");
    throw new Error(
      "Slack app not initialized. Call initializeTools() first."
    );
  }

  if (!input.slackUserId || !input.message) {
    console.log("Both slackUserId and message are required parameters.");
    throw new Error("Both slackUserId and message are required parameters.");
  }

  try {
    // Open a DM conversation with the user
    const dmResult = await slackApp.client.conversations.open({
      users: input.slackUserId,
    });

    if (!dmResult.ok) {
      console.log(`Failed to open DM with user ${input.slackUserId}: ${dmResult.error}`);
      throw new Error(
        `Failed to open DM with user ${input.slackUserId}: ${dmResult.error}`
      );
    }

    const channelId = dmResult.channel.id;

    // Send the message to the DM channel
    const messageResult = await slackApp.client.chat.postMessage({
      channel: channelId,
      text: input.message,
    });

    if (!messageResult.ok) {
      console.log(`Failed to send message to user ${input.slackUserId}: ${messageResult.error}`);
      throw new Error(
        `Failed to send message to user ${input.slackUserId}: ${messageResult.error}`
      );
    }

    console.log(`Successfully sent DM to user ${input.slackUserId}`);
    return { content: [{ type: "text", text: `Successfully sent DM to user ${input.slackUserId}` }] };
  } catch (error) {
    console.log(`Error sending DM to user ${input.slackUserId}: ${error.message}`);
    throw new Error(
      `Error sending DM to user ${input.slackUserId}: ${error.message}`
    );
  }
}

const customMCP = createSdkMcpServer({
  name: "custom_tools",
  version: "1.0.0",
  tools: [getWalletId, getManagerId, getBudgetInfo, sendDM],
});

module.exports = {
  initializeTools,
  customMCP
};
