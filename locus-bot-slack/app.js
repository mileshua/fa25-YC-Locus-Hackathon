const { App } = require('@slack/bolt');

/**
 * This sample slack application uses SocketMode.
 * For the companion getting started setup guide, see:
 * https://tools.slack.dev/bolt-js/getting-started/
 */

// Initializes your app with your bot token and app token
const app = new App({
  token: process.env.SLACK_BOT_TOKEN,
  socketMode: true,
  appToken: process.env.SLACK_APP_TOKEN
});

// Listens to incoming messages that contain "PAYMENT REQUEST"
app.message('PAYMENT REQUEST', async ({ message, say }) => {
  // Create a new thread and echo back the exact same message
  await say({
    text: message.text,
    thread_ts: message.ts // This creates a thread reply to the original message
  });
});

(async () => {
  // Start your app
  await app.start(process.env.PORT || 3000);

  app.logger.info('⚡️ Bolt app is running!');
})();
