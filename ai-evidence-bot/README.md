# AI-Powered Evidence Collection Bot - Review & Control Management

## Architecture
The application uses an AWS Serverless architecture:
- AWS API Gateway
- AWS Lambda (Node.js)
- AWS DynamoDB

## Setup
1. \`npm install\`
2. \`npm run build\`
3. \`npm test\`
4. \`sam build\`
5. \`sam deploy --guided\`

### Local Development
To run API locally:
\`\`\`
sam local start-api
\`\`\`

You can use the provided script to seed data locally if connected to a local DynamoDB instance.

## API Endpoints

### Reviews
- \`POST /reviews\` - Create a review
- \`GET /reviews\` - List reviews
- \`GET /reviews/{reviewId}\` - Get review details
- \`PATCH /reviews/{reviewId}\` - Update review
- \`POST /reviews/{reviewId}/activate\` - Activate review
- \`POST /reviews/{reviewId}/complete\` - Complete review

### Controls
- \`POST /controls\` - Create control
- \`GET /controls\` - List controls
- \`GET /controls/{controlId}\` - Get control

### ReviewControls
- \`POST /reviews/{reviewId}/controls\` - Attach control to review
- \`GET /reviews/{reviewId}/controls\` - List attached controls
- \`GET /review-controls/{reviewControlId}\` - Get ReviewControl details
- \`PATCH /review-controls/{reviewControlId}\` - Update ReviewControl

### Users
- \`GET /users\` - List users
- \`GET /users/{userId}\` - Get user

### Audit Events
- \`GET /reviews/{reviewId}/audit\` - Get review audit trail
- \`GET /review-controls/{reviewControlId}/audit\` - Get review control audit trail

## Example curl request
\`\`\`bash
curl -X POST http://localhost:3000/reviews \\
  -H "X-Actor-Id: USER-LOD2-001" \\
  -H "Content-Type: application/json" \\
  -d '{"name": "AML Q3 2026", "type": "AML_KYC", "startDate": "2026-07-01", "endDate": "2026-09-30"}'
\`\`\`
