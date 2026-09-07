variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Name prefix for all resources"
  type        = string
  default     = "shreyo-agent"
}

variable "lambda_zip_path" {
  description = "Path to the built Lambda deployment zip"
  type        = string
  default     = "../build/lambda.zip"
}

variable "lambda_memory_mb" {
  description = "Memory allocated to the Lambda function"
  type        = number
  default     = 512
}

variable "lambda_timeout_s" {
  description = "Timeout for the Lambda function in seconds"
  type        = number
  default     = 30
}
