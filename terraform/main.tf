terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.5"

  backend "s3" {
    bucket         = "shreyo-jarvis-tfstate-197517025619"
    key            = "jarvis/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "shreyo-jarvis-tf-lock"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}

# ── DynamoDB ───────────────────────────────────────────────────────────────────
resource "aws_dynamodb_table" "agent_data" {
  name         = "shreyo-agent-data"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"

  attribute {
    name = "pk"
    type = "S"
  }

  tags = { Project = "jarvis" }
}

# ── SSM Parameters (secrets) ──────────────────────────────────────────────────
resource "aws_ssm_parameter" "telegram_token" {
  name      = "/shreyo-agent/TELEGRAM_TOKEN"
  type      = "SecureString"
  value     = var.telegram_token
  overwrite = true
}

resource "aws_ssm_parameter" "allowed_user_id" {
  name      = "/shreyo-agent/ALLOWED_USER_ID"
  type      = "SecureString"
  value     = var.allowed_user_id
  overwrite = true
}

resource "aws_ssm_parameter" "groq_api_key" {
  name      = "/shreyo-agent/GROQ_API_KEY"
  type      = "SecureString"
  value     = var.groq_api_key
  overwrite = true
}

resource "aws_ssm_parameter" "gemini_api_key" {
  name      = "/shreyo-agent/GEMINI_API_KEY"
  type      = "SecureString"
  value     = var.gemini_api_key
  overwrite = true
}

# ── IAM Role for Lambda ───────────────────────────────────────────────────────
resource "aws_iam_role" "lambda_role" {
  name = "shreyo-agent-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "shreyo-agent-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # CloudWatch Logs
        Effect = "Allow"
        Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        # DynamoDB
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem",
                    "dynamodb:Scan", "dynamodb:Query", "dynamodb:UpdateItem"]
        Resource = aws_dynamodb_table.agent_data.arn
      },
      {
        # SSM Parameter Store
        Effect   = "Allow"
        Action   = ["ssm:GetParameter", "ssm:GetParameters"]
        Resource = "arn:aws:ssm:${var.aws_region}:*:parameter/shreyo-agent/*"
      },
      {
        # Polly — British neural/standard voice for spoken replies
        Effect   = "Allow"
        Action   = ["polly:SynthesizeSpeech"]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ── Lambda Function ───────────────────────────────────────────────────────────
resource "aws_lambda_function" "jarvis_bot" {
  function_name    = "shreyo-jarvis-bot"
  role             = aws_iam_role.lambda_role.arn
  handler          = "bot.lambda_handler"
  runtime          = "python3.12"
  filename         = "../lambda_package.zip"
  source_code_hash = filebase64sha256("../lambda_package.zip")
  timeout          = 120  # STT + multi-agent + TTS
  memory_size      = 1024

  environment {
    variables = {
      AWS_REGION_NAME      = var.aws_region
      DYNAMO_TABLE         = aws_dynamodb_table.agent_data.name
      JARVIS_VOICE         = "Charon"
      JARVIS_TTS_PROVIDER  = "auto"
      # Secrets are pulled from SSM at runtime — not stored in env vars
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda_policy,
    aws_iam_role_policy_attachment.basic_execution,
  ]

  tags = { Project = "jarvis" }
}

resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.jarvis_bot.function_name}"
  retention_in_days = 7
}

# ── API Gateway HTTP API ──────────────────────────────────────────────────────
resource "aws_apigatewayv2_api" "telegram_webhook" {
  name          = "shreyo-jarvis-webhook"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["content-type", "authorization", "x-desk-token"]
    max_age       = 86400
  }
}

resource "aws_cloudwatch_event_rule" "jarvis_tick" {
  name                = "shreyo-jarvis-reminder-tick"
  schedule_expression = "rate(5 minutes)"
}

resource "aws_cloudwatch_event_target" "jarvis_tick" {
  rule      = aws_cloudwatch_event_rule.jarvis_tick.name
  target_id = "jarvis"
  arn       = aws_lambda_function.jarvis_bot.arn
}

resource "aws_lambda_permission" "events_tick" {
  statement_id  = "AllowEventBridgeTick"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.jarvis_bot.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.jarvis_tick.arn
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.telegram_webhook.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.jarvis_bot.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "webhook_route" {
  api_id    = aws_apigatewayv2_api.telegram_webhook.id
  route_key = "POST /webhook"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "options_webhook" {
  api_id    = aws_apigatewayv2_api.telegram_webhook.id
  route_key = "OPTIONS /webhook"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_stage" "default_stage" {
  api_id      = aws_apigatewayv2_api.telegram_webhook.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigw_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.jarvis_bot.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.telegram_webhook.execution_arn}/*/*"
}
