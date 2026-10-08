const express = require('express');
const cors = require('cors');
const dynamodbLocal = require('dynamodb-local');
const { DynamoDBClient, CreateTableCommand } = require('@aws-sdk/client-dynamodb');
const fs = require('fs');

const PORT = 3000;
process.env.AWS_SAM_LOCAL = 'true';
process.env.AWS_REGION = 'us-east-1';
process.env.AWS_ACCESS_KEY_ID = 'mock';
process.env.AWS_SECRET_ACCESS_KEY = 'mock';
process.env.REVIEWS_TABLE = 'ReviewsTable';
process.env.CONTROLS_TABLE = 'ControlsTable';
process.env.REVIEW_CONTROLS_TABLE = 'ReviewControlsTable';
process.env.USERS_TABLE = 'UsersTable';
process.env.AUDIT_EVENTS_TABLE = 'AuditEventsTable';

const app = express();
app.use(cors());
app.use(express.json());

// Import compiled lambda handlers
const reviewHandler = require('./dist/reviews/handler');
const controlHandler = require('./dist/controls/handler');
const rcHandler = require('./dist/review-controls/handler');
const userHandler = require('./dist/users/handler');
const auditHandler = require('./dist/audit/handler');

// Helper to convert Express request to API Gateway event
function wrap(handler) {
  return async (req, res) => {
    const event = {
      pathParameters: req.params || {},
      queryStringParameters: req.query || {},
      headers: req.headers || {},
      body: req.body && Object.keys(req.body).length ? JSON.stringify(req.body) : null
    };
    try {
      const result = await handler(event);
      res.status(result.statusCode || 200).set(result.headers || {}).send(result.body || "{}");
    } catch (err) {
      console.error(err);
      res.status(500).json({ error: 'Internal Server Error' });
    }
  };
}

// Routes
app.post('/reviews', wrap(reviewHandler.create));
app.get('/reviews', wrap(reviewHandler.list));
app.get('/reviews/:reviewId', wrap(reviewHandler.get));
app.patch('/reviews/:reviewId', wrap(reviewHandler.update));
app.post('/reviews/:reviewId/activate', wrap(reviewHandler.activate));
app.post('/reviews/:reviewId/complete', wrap(reviewHandler.complete));

app.post('/controls', wrap(controlHandler.create));
app.get('/controls', wrap(controlHandler.list));
app.get('/controls/:controlId', wrap(controlHandler.get));
app.patch('/controls/:controlId', wrap(controlHandler.update));

app.post('/reviews/:reviewId/controls', wrap(rcHandler.attachControl));
app.get('/reviews/:reviewId/controls', wrap(rcHandler.listControlsForReview));
app.get('/review-controls/:reviewControlId', wrap(rcHandler.getDetails));
app.patch('/review-controls/:reviewControlId', wrap(rcHandler.update));

app.get('/users', wrap(userHandler.list));
app.get('/users/:userId', wrap(userHandler.get));

app.get('/reviews/:reviewId/audit', wrap(auditHandler.getReviewAudit));
app.get('/review-controls/:reviewControlId/audit', wrap(auditHandler.getReviewControlAudit));

async function createTables() {
  const client = new DynamoDBClient({ endpoint: 'http://127.0.0.1:8000', region: 'us-east-1' });
  const tables = [
    {
      TableName: 'ReviewsTable',
      AttributeDefinitions: [{ AttributeName: 'reviewId', AttributeType: 'S' }],
      KeySchema: [{ AttributeName: 'reviewId', KeyType: 'HASH' }],
      BillingMode: 'PAY_PER_REQUEST'
    },
    {
      TableName: 'ControlsTable',
      AttributeDefinitions: [{ AttributeName: 'controlId', AttributeType: 'S' }],
      KeySchema: [{ AttributeName: 'controlId', KeyType: 'HASH' }],
      BillingMode: 'PAY_PER_REQUEST'
    },
    {
      TableName: 'ReviewControlsTable',
      AttributeDefinitions: [
        { AttributeName: 'reviewControlId', AttributeType: 'S' },
        { AttributeName: 'reviewId', AttributeType: 'S' },
        { AttributeName: 'controlId', AttributeType: 'S' }
      ],
      KeySchema: [{ AttributeName: 'reviewControlId', KeyType: 'HASH' }],
      GlobalSecondaryIndexes: [
        {
          IndexName: 'reviewId-index',
          KeySchema: [{ AttributeName: 'reviewId', KeyType: 'HASH' }],
          Projection: { ProjectionType: 'ALL' }
        },
        {
          IndexName: 'controlId-index',
          KeySchema: [{ AttributeName: 'controlId', KeyType: 'HASH' }],
          Projection: { ProjectionType: 'ALL' }
        }
      ],
      BillingMode: 'PAY_PER_REQUEST'
    },
    {
      TableName: 'UsersTable',
      AttributeDefinitions: [{ AttributeName: 'userId', AttributeType: 'S' }],
      KeySchema: [{ AttributeName: 'userId', KeyType: 'HASH' }],
      BillingMode: 'PAY_PER_REQUEST'
    },
    {
      TableName: 'AuditEventsTable',
      AttributeDefinitions: [
        { AttributeName: 'auditId', AttributeType: 'S' },
        { AttributeName: 'entityId', AttributeType: 'S' }
      ],
      KeySchema: [{ AttributeName: 'auditId', KeyType: 'HASH' }],
      GlobalSecondaryIndexes: [
        {
          IndexName: 'entityId-index',
          KeySchema: [{ AttributeName: 'entityId', KeyType: 'HASH' }],
          Projection: { ProjectionType: 'ALL' }
        }
      ],
      BillingMode: 'PAY_PER_REQUEST'
    }
  ];

  for (const t of tables) {
    try {
      await client.send(new CreateTableCommand(t));
      console.log('Created table ' + t.TableName);
    } catch (err) {
      if (err.name !== 'ResourceInUseException') {
        console.error(err);
      }
    }
  }
}

async function start() {
  console.log('Starting DynamoDB Local...');
  dynamodbLocal.launch(8000, null, ['-sharedDb']);
  
  // wait a bit for DB to start
  setTimeout(async () => {
    await createTables();
    console.log('Seeding initial data...');
    require('./scripts/seed.js');

    app.listen(PORT, () => {
      console.log('\n=========================================');
      console.log('🚀 Local Server running on http://localhost:' + PORT);
      console.log('=========================================');
      console.log('Test it out with:');
      console.log('curl http://localhost:' + PORT + '/users');
      console.log('curl http://localhost:' + PORT + '/controls');
    });
  }, 2000);
}

start();
