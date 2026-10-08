import { PutCommand, GetCommand, QueryCommand } from "@aws-sdk/lib-dynamodb";
import { docClient } from "../shared/db";
import { ReviewControl } from "../shared/types";

const TABLE_NAME = process.env.REVIEW_CONTROLS_TABLE || '';

export async function saveReviewControl(rc: ReviewControl): Promise<void> {
  await docClient.send(new PutCommand({
    TableName: TABLE_NAME,
    Item: rc
  }));
}

export async function getReviewControl(rcId: string): Promise<ReviewControl | null> {
  const result = await docClient.send(new GetCommand({
    TableName: TABLE_NAME,
    Key: { reviewControlId: rcId }
  }));
  return (result.Item as ReviewControl) || null;
}

export async function listReviewControls(reviewId: string): Promise<ReviewControl[]> {
  const result = await docClient.send(new QueryCommand({
    TableName: TABLE_NAME,
    IndexName: 'reviewId-index',
    KeyConditionExpression: 'reviewId = :rid',
    ExpressionAttributeValues: {
      ':rid': reviewId
    }
  }));
  return (result.Items || []) as ReviewControl[];
}
