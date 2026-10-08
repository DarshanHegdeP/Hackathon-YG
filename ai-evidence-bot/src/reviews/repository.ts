import { PutCommand, GetCommand, ScanCommand } from "@aws-sdk/lib-dynamodb";
import { docClient } from "../shared/db";
import { Review } from "../shared/types";

const TABLE_NAME = process.env.REVIEWS_TABLE || '';

export async function saveReview(review: Review): Promise<void> {
  await docClient.send(new PutCommand({
    TableName: TABLE_NAME,
    Item: review
  }));
}

export async function getReview(reviewId: string): Promise<Review | null> {
  const result = await docClient.send(new GetCommand({
    TableName: TABLE_NAME,
    Key: { reviewId }
  }));
  return (result.Item as Review) || null;
}

export async function listReviews(filters: any): Promise<Review[]> {
  const result = await docClient.send(new ScanCommand({
    TableName: TABLE_NAME
  }));
  let reviews = (result.Items || []) as Review[];
  if (filters.status) reviews = reviews.filter(r => r.status === filters.status);
  if (filters.type) reviews = reviews.filter(r => r.type === filters.type);
  return reviews;
}
