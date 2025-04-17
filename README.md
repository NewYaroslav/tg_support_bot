# tg_support_bot

**Telegram-бот для автоматизации приёма и обработки обращений в техническую поддержку внутри компании.**

## 🚀 Возможности

- Авторизация сотрудников по корпоративному email (с проверкой по белому списку)
- Автоматическое добавление новых email-адресов с возможностью блокировки
- Интерфейс выбора категории обращения через Telegram-клавиатуру
- Ввод текста обращения и отправка в Telegram-группу и/или на email
- Поддержка состояний, шаблонов и персонализированных сообщений
- Гибкая настройка поведения через YAML-файлы
- Использование Jinja2 для генерации текста и HTML-писем
- Логирование в файл и консоль

## 📦 Установка

> Убедитесь, что у вас установлен Python 3.9 или выше.

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/yourname/tg_support_bot.git
   cd tg_support_bot
   ```

2. Создайте и активируйте виртуальное окружение:
   ```bash
   python -m venv venv
   call venv\Scripts\activate  # Windows
   source venv/bin/activate    # Linux/macOS
   ```

3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

Или просто запустите:

```bash
setup.bat
```

## ▶️ Запуск

Для запуска Telegram-бота:

```bash
start_bot.bat      # Windows
./start_bot.sh     # Linux/macOS
```

Для тестовой отправки email:

```bash
start_test_email.bat
```

## ⚙️ Конфигурационные файлы

### `.env`

В файле `.env` указываются ключевые параметры:

```dotenv
BOT_TOKEN=your_bot_token
EMAIL_SENDER=bot@yourcompany.com
EMAIL_PASSWORD=app_password
SMTP_SERVER=smtp.yourcompany.com
SMTP_PORT=587
SUPPORT_EMAIL=support@yourcompany.com
SUPPORT_CHAT_ID=-1001234567890
LOG_LEVEL=DEBUG
```

### `config/auth.yaml`

Конфигурация авторизации:

```yaml
auth:
  email_pattern: "^[a-zA-Z0-9_.+-]+@yourcompany\.com$"
  email_autocomplete: "@yourcompany.com"
  allow_incomplete_input: true
  send_welcome_before_topic: true
  send_topic_after_auth: true
  delay_after_auth_success: 2
```

### `config/ui_config.yaml`

Файл конфигурации пользовательского интерфейса, в том числе:
- команды меню,
- начальное поведение при авторизации,
- категории тикетов,
- ограничения.

Конфигурация интерфейса:

```yaml
telegram_menu:
  - command: start
    description: "Обратиться за помощью"
  - command: help
    description: "Показать справку"
  - command: myid
    description: "Показать ID и email (если есть)"

telegram_start:
  show_action_button_if_authorized: true
  action_button_text: "📨 Отправить обращение"

authorization:
  confirm_change_buttons:
    yes: "✅ Да"
    no: "❌ Нет"

  email_status_labels:
    allowed: "✅ Разрешён"
    banned: "🚫 Забанен"

ticket_categories:
  - "💻 Аппаратные сбои"
  - "🛠 Программные ошибки"
  - "🌐 Сетевые проблемы"
  - "🔑 Запросы на доступ"
  - "🛡 Кибербезопасность"
  - "❗ Жалоба/Благодарность"
  - "📁 Другое"

message_limits:
  max_submission_length: 1500
```

## 📁 Шаблоны сообщений

Файлы шаблонов находятся в папке `templates/`. Они позволяют гибко кастомизировать текст сообщений:

| Файл                    | Назначение |
|-------------------------|------------|
| auth_start.txt          | Приветствие при входе, если пользователь не авторизован |
| auth_success.txt        | Уведомление об успешной авторизации |
| auth_already.txt        | Пользователь уже авторизован |
| auth_not_registered.txt | Email не найден в базе |
| auth_banned.txt         | Email в базе, но помечен как заблокированный |
| auth_invalid.txt        | Введён некорректный email |
| auth_change_confirm.txt | Подтверждение смены email |
| auth_changed.txt        | Уведомление об успешной смене email |
| auth_change_cancelled.txt | Смена email отменена |
| welcome_user.txt        | Приветствие для авторизованного пользователя |
| select_topic.txt        | Выбор категории обращения |
| enter_message.txt       | Просьба ввести текст обращения |
| invalid_topic.txt       | Ошибка при вводе некорректной категории |
| invalid_input.txt       | Введено что-то не по формату/не в нужный момент |
| message_too_long.txt    | Сообщение слишком длинное |
| ticket_sent.txt         | Подтверждение успешной отправки обращения |
| ticket_summary.txt      | Итоговое сообщение, отправляемое в Telegram и/или email |
| email_added.txt         | Успешное добавление email |
| email_banned.txt        | Успешная блокировка email |
| email_removed.txt       | Успешное удаление email |
| email_required.txt      | Email не указан при вызове команды |
| email_status_found.txt  | Статус указанного email (разрешён/забанен) |
| email_status_not_found.txt | Email не найден |
| my_id.txt               | Сообщение с ID пользователя и email (если есть) |
| not_authorized.txt      | Ошибка: команда доступна только администраторам |
| help_user.txt           | Справка для обычных пользователей |
| help_admin.txt          | Справка для администраторов |
| support_email.html      | HTML-шаблон email сообщения для поддержки |

## Запуск через pyproject.toml

Если используется `pyproject.toml`, доступен CLI:

```bash
tg-support-bot
```

## Лицензия

MIT License
