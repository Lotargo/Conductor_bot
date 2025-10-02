# Kafka settings
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
KAFKA_TOPIC_WHATSAPP_NOTIFICATIONS = 'whatsapp_notification_screenshots'
KAFKA_TOPIC_TELEGRAM_NOTIFICATIONS = 'telegram_notification_screenshots' # Новый топик
KAFKA_TOPIC_DECISIONS = 'decision_requests'
KAFKA_TOPIC_ACTIONS = 'execution_actions'

# Google Gemini API Key
GEMINI_API_KEY = 'YOUR_GEMINI_API_KEY'  # Placeholder

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN' # Placeholder

# Timeout for orchestrator
ORCHESTRATOR_TIMEOUT = 60  # in seconds