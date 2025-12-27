"""Configuration module - centralized environment variable access"""
import os

# Google Sheets constants
GOOGLE_SHEETS_INBOX_LOG_TAB = "inbox_log"


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


def get_telegram_bot_token_param_name() -> str:
    """Get Telegram bot token parameter name from environment.

    The parameter name points to the SSM Parameter Store parameter that contains the actual token.

    Reference: docs/stories/2.3.story.md AC 5
    """
    param_name = os.getenv("TELEGRAM_BOT_TOKEN_PARAM_NAME")
    if not param_name:
        raise ValueError("TELEGRAM_BOT_TOKEN_PARAM_NAME environment variable is required")
    return param_name


def get_telegram_bot_token() -> str:
    """Get Telegram bot token from SSM Parameter Store.

    Reads the parameter name from environment variable, then retrieves the actual token
    from SSM Parameter Store (SecureString).

    Reference: docs/stories/2.3.story.md AC 5
    """
    from talktalk_shared.utils.secrets import get_parameter

    param_name = get_telegram_bot_token_param_name()
    return get_parameter(param_name)


def get_telegram_chat_id() -> str:
    """Get Telegram chat ID from environment"""
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        raise ValueError("TELEGRAM_CHAT_ID environment variable is required")
    return chat_id


def get_aggregation_state_table() -> str:
    """Get AggregationState DynamoDB table name"""
    table = os.getenv("AGGREGATION_STATE_TABLE")
    if not table:
        raise ValueError("AGGREGATION_STATE_TABLE environment variable is required")
    return table


def get_aggregation_trigger_queue_url() -> str:
    """Get AggregationTriggerQueue SQS URL"""
    queue_url = os.getenv("AGGREGATION_TRIGGER_QUEUE_URL")
    if not queue_url:
        raise ValueError("AGGREGATION_TRIGGER_QUEUE_URL environment variable is required")
    return queue_url


def get_enable_message_aggregation() -> bool:
    """Get message aggregation feature flag (default: False)"""
    return os.getenv("ENABLE_MESSAGE_AGGREGATION", "false").lower() == "true"


def get_aggregation_window_seconds() -> int:
    """Get aggregation time window in seconds (default: 30)"""
    return int(os.getenv("AGGREGATION_WINDOW_SECONDS", "30"))


def get_max_messages_per_aggregation() -> int:
    """Get maximum messages per aggregation session (default: 10)"""
    return int(os.getenv("MAX_MESSAGES_PER_AGGREGATION", "10"))


def get_vector_index_metadata_table() -> str:
    """Get VectorIndexMetadata DynamoDB table name"""
    table = os.getenv("VECTOR_INDEX_METADATA_TABLE")
    if not table:
        raise ValueError("VECTOR_INDEX_METADATA_TABLE environment variable is required")
    return table


def get_vector_index_bucket() -> str:
    """Get S3 bucket name for vector indices"""
    bucket = os.getenv("VECTOR_INDEX_BUCKET")
    if not bucket:
        raise ValueError("VECTOR_INDEX_BUCKET environment variable is required")
    return bucket


def get_google_sheets_spreadsheet_id() -> str:
    """Get Google Sheets Spreadsheet ID for logging"""
    spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
    if not spreadsheet_id:
        raise ValueError("GOOGLE_SHEETS_SPREADSHEET_ID environment variable is required")
    return spreadsheet_id


def get_openai_api_key_param_name() -> str:
    """Get OpenAI API key parameter name from environment.

    The parameter name points to the SSM Parameter Store parameter that contains the actual API key.

    Reference: docs/architecture.md#aws-components-summary
    """
    param_name = os.getenv("OPENAI_API_KEY_PARAM_NAME")
    if not param_name:
        raise ValueError("OPENAI_API_KEY_PARAM_NAME environment variable is required")
    return param_name


def get_openai_api_key() -> str:
    """Get OpenAI API key from SSM Parameter Store.

    Reads the parameter name from environment variable, then retrieves the actual key
    from SSM Parameter Store (SecureString).

    Reference: docs/architecture.md#aws-components-summary
    """
    from talktalk_shared.utils.secrets import get_parameter

    param_name = get_openai_api_key_param_name()
    return get_parameter(param_name)


def get_google_sa_json_param_name() -> str:
    """Get Google Service Account JSON parameter name from environment.

    The parameter name points to the SSM Parameter Store parameter that contains the SA JSON.

    Reference: docs/architecture.md#aws-components-summary
    """
    param_name = os.getenv("GOOGLE_SA_JSON_PARAM_NAME")
    if not param_name:
        raise ValueError("GOOGLE_SA_JSON_PARAM_NAME environment variable is required")
    return param_name


def get_google_sa_json() -> str:
    """Get Google Service Account JSON from SSM Parameter Store.

    Reads the parameter name from environment variable, then retrieves the actual SA JSON
    from SSM Parameter Store (SecureString).

    Reference: docs/architecture.md#aws-components-summary
    """
    from talktalk_shared.utils.secrets import get_parameter

    param_name = get_google_sa_json_param_name()
    return get_parameter(param_name)
