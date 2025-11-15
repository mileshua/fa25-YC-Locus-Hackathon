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
