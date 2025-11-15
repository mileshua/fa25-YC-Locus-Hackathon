const fs = require("fs");
const path = require("path");

/**
 * Get wallet ID for a given Slack user ID
 * @param {string} slackUserId - The Slack user ID
 * @returns {string} - Wallet ID or error message
 */
function getWalletId(slackUserId) {
  const walletPath = path.join(__dirname, "wallet.json");
  
  if (!fs.existsSync(walletPath)) {
    throw new Error("wallet.json file not found. Please ensure the wallet mapping file exists.");
  }
  
  const walletData = JSON.parse(fs.readFileSync(walletPath, "utf8"));
  
  if (!walletData[slackUserId]) {
    throw new Error(`No wallet ID found for Slack user ${slackUserId}. User may not be registered in the wallet system.`);
  }
  
  return walletData[slackUserId];
}

/**
 * Get manager ID for a given Slack user ID
 * @param {string} slackUserId - The Slack user ID
 * @returns {string} - Manager's Slack ID or empty string if no manager, or error message
 */
function getManagerId(slackUserId) {
  const hierarchyPath = path.join(__dirname, "hierarchy.json");
  
  if (!fs.existsSync(hierarchyPath)) {
    throw new Error("hierarchy.json file not found. Please ensure the hierarchy mapping file exists.");
  }
  
  const hierarchyData = JSON.parse(fs.readFileSync(hierarchyPath, "utf8"));
  
  if (!hierarchyData.hasOwnProperty(slackUserId)) {
    throw new Error(`No hierarchy information found for Slack user ${slackUserId}. User may not be registered in the hierarchy system.`);
  }
  
  // Return the manager ID (could be empty string if no manager)
  return hierarchyData[slackUserId];
}

/**
 * Get budget information for a given Slack user ID
 * @param {string} slackUserId - The Slack user ID
 * @returns {Object|string} - Budget object with total_budget and dollars_spent, or error message
 */
function getBudgetInfo(slackUserId) {
  const budgetPath = path.join(__dirname, "budget.json");
  
  if (!fs.existsSync(budgetPath)) {
    throw new Error("budget.json file not found. Please ensure the budget mapping file exists.");
  }
  
  const budgetData = JSON.parse(fs.readFileSync(budgetPath, "utf8"));
  
  if (!budgetData[slackUserId]) {
    throw new Error(`No budget information found for Slack user ${slackUserId}. User may not be registered in the budget system.`);
  }
  
  return budgetData[slackUserId];
}

module.exports = {
  getWalletId,
  getManagerId,
  getBudgetInfo
};
