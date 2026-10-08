const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const { DynamoDBDocumentClient, PutCommand } = require("@aws-sdk/lib-dynamodb");
const fs = require('fs');

const client = new DynamoDBClient({
  endpoint: process.env.AWS_SAM_LOCAL ? "http://127.0.0.1:8000" : undefined,
});
const docClient = DynamoDBDocumentClient.from(client);

async function seed() {
  const controls = JSON.parse(fs.readFileSync('./seed/controls.json', 'utf8'));
  const users = JSON.parse(fs.readFileSync('./seed/users.json', 'utf8'));

  console.log('Seeding controls...');
  for (const c of controls) {
    await docClient.send(new PutCommand({
      TableName: process.env.CONTROLS_TABLE || 'ControlsTable',
      Item: { ...c, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() }
    }));
  }

  console.log('Seeding users...');
  for (const u of users) {
    await docClient.send(new PutCommand({
      TableName: process.env.USERS_TABLE || 'UsersTable',
      Item: u
    }));
  }
  console.log('Done.');
}
seed().catch(console.error);
