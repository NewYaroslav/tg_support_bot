import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound

logger = logging.getLogger("tg_support_bot.template")

env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["txt", "html"])
)

def render_template(template_name: str, fallback: str = "⚠ Template error", **kwargs) -> str:
    """
    Renders a template safely.

    @param template_name: Template filename from /templates
    @param fallback: Text to return on error
    @param kwargs: Template context
    @return Rendered string or fallback
    """
    try:
        template = env.get_template(template_name)
        return template.render(**kwargs)
    except TemplateNotFound:
        logger.error(f"Template not found: {template_name}")
        return f"[ERROR] Template '{template_name}' not found"
    except Exception as e:
        logger.error(f"Template rendering failed: {e}")
        return fallback