variable "aws_region" {
  description = "AWS region to deploy in"
  type        = string
  default     = "ap-south-1"  # Mumbai — lowest latency for India
}

variable "telegram_token" {
  description = "Telegram bot token from @BotFather"
  type        = string
  sensitive   = true
}

variable "allowed_user_id" {
  description = "Your Telegram numeric user ID (from @userinfobot)"
  type        = string
  sensitive   = true
}

variable "groq_api_key" {
  description = "Groq API key from console.groq.com"
  type        = string
  sensitive   = true
}

variable "gemini_api_key" {
  description = "Google Gemini API key from aistudio.google.com"
  type        = string
  sensitive   = true
}
