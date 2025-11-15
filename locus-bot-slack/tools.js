const fs = require("fs");
const path = require("path");
// Remove betaTool import as we'll define tools in Claude Agent SDK format

// Store reference to Slack app for DM functionality
let slackApp = null;

function initializeTools(app) {
  slackApp = app;
}

// Tool definition for Claude Agent SDK
const getWalletId = {
  name: "getWalletId",
  description: "Get wallet ID for a given Slack user ID",
  inputSchema: {
    type: "object",
    properties: {
      slackUserId: {
        type: "string",
        description: "The Slack user ID to look up",
      },
    },
    required: ["slackUserId"],
  },
};

// Tool implementation function
async function getWalletIdImpl(input) {
  const walletPath = path.join(__dirname, "wallet.json");

  if (!fs.existsSync(walletPath)) {
    throw new Error(
      "wallet.json file not found. Please ensure the wallet mapping file exists."
    );
  }

  const walletData = JSON.parse(fs.readFileSync(walletPath, "utf8"));

  if (!walletData[input.slackUserId]) {
    throw new Error(
      `No wallet ID found for Slack user ${input.slackUserId}. User may not be registered in the wallet system.`
    );
  }

  return walletData[input.slackUserId];
}

const getManagerId = {
  name: "getManagerId",
  description: "Get manager ID for a given Slack user ID. Returns empty string if no manager.",
  inputSchema: {
    type: "object",
    properties: {
      slackUserId: {
        type: "string",
        description: "The Slack user ID to look up",
      },
    },
    required: ["slackUserId"],
  },
};

async function getManagerIdImpl(input) {
  const hierarchyPath = path.join(__dirname, "hierarchy.json");

  if (!fs.existsSync(hierarchyPath)) {
    throw new Error(
      "hierarchy.json file not found. Please ensure the hierarchy mapping file exists."
    );
  }

  const hierarchyData = JSON.parse(fs.readFileSync(hierarchyPath, "utf8"));

  if (!hierarchyData.hasOwnProperty(input.slackUserId)) {
    throw new Error(
      `No hierarchy information found for Slack user ${input.slackUserId}. User may not be registered in the hierarchy system.`
    );
  }

  // Return the manager ID (could be empty string if no manager)
  return hierarchyData[input.slackUserId];
}

const getBudgetInfo = {
  name: "getBudgetInfo",
  description: "Get budget information for a given Slack user ID, including total budget and dollars spent",
  inputSchema: {
    type: "object",
    properties: {
      slackUserId: {
        type: "string",
        description: "The Slack user ID to look up",
      },
    },
    required: ["slackUserId"],
  },
};

async function getBudgetInfoImpl(input) {
  const budgetPath = path.join(__dirname, "budget.json");

  if (!fs.existsSync(budgetPath)) {
    throw new Error(
      "budget.json file not found. Please ensure the budget mapping file exists."
    );
  }

  const budgetData = JSON.parse(fs.readFileSync(budgetPath, "utf8"));

  if (!budgetData.hasOwnProperty(input.slackUserId)) {
    throw new Error(
      `No budget information found for Slack user ${input.slackUserId}. User may not be registered in the budget system.`
    );
  }

  return budgetData[input.slackUserId];
}

const sendDM = {
  name: "sendDM",
  description: "Send a direct message to a Slack user",
  inputSchema: {
    type: "object",
    properties: {
      slackUserId: {
        type: "string",
        description: "The Slack user ID to send message to",
      },
      message: {
        type: "string",
        description: "The message to send",
      },
    },
    required: ["slackUserId", "message"],
  },
};

async function sendDMImpl(input) {
  if (!slackApp) {
    throw new Error(
      "Slack app not initialized. Call initializeTools() first."
    );
  }

  if (!input.slackUserId || !input.message) {
    throw new Error("Both slackUserId and message are required parameters.");
  }

  try {
    // Open a DM conversation with the user
    const dmResult = await slackApp.client.conversations.open({
      users: input.slackUserId,
    });

    if (!dmResult.ok) {
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
      throw new Error(
        `Failed to send message to user ${input.slackUserId}: ${messageResult.error}`
      );
    }

    return `Successfully sent DM to user ${input.slackUserId}`;
  } catch (error) {
    throw new Error(
      `Error sending DM to user ${input.slackUserId}: ${error.message}`
    );
  }
}

module.exports = {
  initializeTools,
  getWalletId,
  getManagerId,
  getBudgetInfo,
  sendDM,
  getWalletIdImpl,
  getManagerIdImpl,
  getBudgetInfoImpl,
  sendDMImpl
};
