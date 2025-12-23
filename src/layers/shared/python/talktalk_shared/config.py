"""Configuration module - centralized environment variable access"""
import os


def get_aws_region() -> str:
    """Get AWS region from environment"""
    return os.getenv("AWS_REGION", "ap-northeast-2")


def get_channel_config_table() -> str:
    """Get ChannelConfig DynamoDB table name"""
    table = os.getenv("CHANNEL_CONFIG_TABLE")
    if not table:
        raise ValueError("CHANNEL_CONFIG_TABLE environment variable is required")
    return table


def get_deduplication_table() -> str:
    """Get Deduplication DynamoDB table name"""
    table = os.getenv("DEDUPLICATION_TABLE")
    if not table:
        raise ValueError("DEDUPLICATION_TABLE environment variable is required")
    return table


def get_global_mode_table() -> str:
    """Get GlobalMode DynamoDB table name"""
    table = os.getenv("GLOBAL_MODE_TABLE")
    if not table:
        raise ValueError("GLOBAL_MODE_TABLE environment variable is required")
    return table


def get_worker_queue_url() -> str:
    """Get Worker Queue SQS URL"""
    queue_url = os.getenv("WORKER_QUEUE_URL")
    if not queue_url:
        raise ValueError("WORKER_QUEUE_URL environment variable is required")
    return queue_url


def get_log_level() -> str:
    """Get logging level"""
    return os.getenv("LOG_LEVEL", "INFO")


def get_service_name() -> str:
    """Get service name for logging"""
    return os.getenv("SERVICE_NAME", "talktalk-auto")


def get_telegram_bot_token() -> str:
    """Get Telegram bot token from environment"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
    return token


def get_telegram_chat_id() -> str:
    """Get Telegram chat ID from environment"""
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        raise ValueError("TELEGRAM_CHAT_ID environment variable is required")
    return chat_id
