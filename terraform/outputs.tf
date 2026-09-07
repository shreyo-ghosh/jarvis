output "webhook_url" {
  description = "Paste this into set_webhook.sh or Telegram setWebhook call"
  value       = "${aws_apigatewayv2_api.telegram_webhook.api_endpoint}/webhook"
}

output "lambda_function_name" {
  description = "Lambda function name for CloudWatch logs"
  value       = aws_lambda_function.jarvis_bot.function_name
}

output "dynamodb_table" {
  description = "DynamoDB table storing revenue, tasks, watchlist"
  value       = aws_dynamodb_table.agent_data.name
}

output "log_group" {
  description = "CloudWatch log group — check here if bot isn't responding"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}
