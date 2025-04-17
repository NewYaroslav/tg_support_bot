import os
import logging
import smtplib
from modules.logging_config import logger
from email.message import EmailMessage
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape
from rich.console import Console
from modules.template_engine import render_template

console = Console()

load_dotenv()
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

def send_email(subject: str, to_address: str, text_body: str = "", html_body: str = None):
    """
    Sends an email via SMTP with optional HTML version.

    @param subject: Email subject
    @param to_address: Recipient email
    @param text_body: Fallback text version
    @param html_body: Optional HTML version
    @throws Exception on failure
    """
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = to_address
        msg.set_content(text_body or " ")

        if html_body:
            msg.add_alternative(html_body, subtype='html')

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email sent to {to_address}")

    except Exception as e:
        logger.error(f"Failed to send email to {to_address}: {e}")
        raise
        
if __name__ == "__main__":
    console.rule("[bold green]Email Test Mode[/bold green]")
    try:
        to_address = input("Recipient email: ").strip()
        subject = input("Subject: ").strip()
        text_body = input("Text message (plain): ").strip()

        use_template = input("Use HTML template? (y/n): ").lower().strip() == "y"
        html_body = None

        if use_template:
            template_name = input("Template filename (default: support_email.html): ").strip() or "support_email.html"
            email = input("User email: ").strip()
            telegram_username = input("Telegram username: ").strip()
            topic = input("Topic: ").strip()
            message = input("Message: ").strip()

            logger.info("Rendering HTML template...")
            html_body = render_template(
                template_name,
                email=email,
                telegram_username=telegram_username,
                topic=topic,
                message=message
            )
            console.print("[green][OK] HTML rendered successfully[/green]")

        logger.info("Sending email...")
        send_email(subject, to_address, text_body, html_body)
        console.print(f"[bold green][OK] Email sent to [white]{to_address}[/white][/bold green]")

    except KeyboardInterrupt:
        console.print("\n[yellow][!] Cancelled by user.[/yellow]")
    except Exception as e:
        logger.exception("An unexpected error occurred")
        console.print(f"[bold red][FAIL] Failed:[/bold red] {e}")
