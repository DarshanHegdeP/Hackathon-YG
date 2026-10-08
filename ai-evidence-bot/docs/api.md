# API Documentation

## Review API
\`POST /reviews\`
Request:
\`\`\`json
{
  "name": "AML Q3 2026",
  "type": "AML_KYC",
  "startDate": "2026-07-01",
  "endDate": "2026-09-30",
  "businessUnits": ["RETAIL"],
  "description": "Desc"
}
\`\`\`
Response:
\`\`\`json
{
  "data": { "reviewId": "REV-xxx", ... }
}
\`\`\`

\`GET /reviews/{reviewId}\`
Response: returns the review

\`PATCH /reviews/{reviewId}\`
Update fields.

\`POST /reviews/{reviewId}/activate\`
Activates a review if validation passes.

\`POST /reviews/{reviewId}/complete\`
Completes a review.

## Control API
\`POST /controls\`
\`GET /controls\`
\`GET /controls/{controlId}\`
\`PATCH /controls/{controlId}\`

## ReviewControl API
\`POST /reviews/{reviewId}/controls\`
Request:
\`\`\`json
{
  "controlId": "AML-001",
  "ownerId": "USER-1"
}
\`\`\`

\`GET /reviews/{reviewId}/controls\`
\`GET /review-controls/{reviewControlId}\`
\`PATCH /review-controls/{reviewControlId}\`

## User API
\`GET /users\`
\`GET /users/{userId}\`

## Audit API
\`GET /reviews/{reviewId}/audit\`
\`GET /review-controls/{reviewControlId}/audit\`
