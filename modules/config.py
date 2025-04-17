import yaml

with open("config/ui_config.yaml", "r", encoding="utf-8") as f:
    _ui_config = yaml.safe_load(f)

with open("config/auth.yaml", "r", encoding="utf-8") as f:
    _auth = yaml.safe_load(f)

telegram_menu = _ui_config.get("telegram_menu", [])
telegram_start = _ui_config.get("telegram_start", {})
authorization_ui = _ui_config.get("authorization", {})
ticket_categories = _ui_config.get("ticket_categories", [])
message_limits = _ui_config.get("message_limits", {})
auth_config = _auth.get("auth", {})