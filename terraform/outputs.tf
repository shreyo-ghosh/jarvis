output "webhook_url" {
  description = "Full URL to register as the Telegram webhook"
  value       = "${aws_apigatewayv2_api.bot_api.api_endpoint}/webhook"
}

output "lambda_function_name" {
  value = aws_lambda_function.bot.function_name
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.tracker.name
}
