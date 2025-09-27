import logging
import os
import re
import time

from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

TEMPLATE_DIR = os.getenv(
    "DIGEST_TEMPLATE_DIR", os.path.join(os.path.dirname(__file__), "templates")
)

logger.info("Intializing Jinja2 with template directory: %s", TEMPLATE_DIR)

_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR), autoescape=select_autoescape()
)


def get_template(name: str) -> Template:
    logger.debug("Loading template %r", name)
    try:
        tmpl = _env.get_template(name)
        logger.debug("Template %r loaded successfully", name)
        return tmpl
    except Exception as e:
        logger.exception("Error loading template %r: %s", name, e)
        raise


def render(name: str, **ctx) -> str:
    """
    Load and render the given template with context, logging timing and errors.
    :param name: filename of the template (e.g. 'digest.md.j2')
    :param ctx: keyword args for rendering
    :return: rendered string
    """
    start = time.perf_counter()
    try:
        tmpl = get_template(name)
        result = tmpl.render(**ctx)
        elapsed = (time.perf_counter() - start) * 1000
        logger.info("Rendered template %r in %.2fms", name, elapsed)
        return result
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        logger.exception(
            "Error rendering template %r after %.2fms with context %r: %s",
            name,
            elapsed,
            ctx,
            e,
        )
        raise


def validate_markdown(md: str):
    if not md.strip():
        raise ValueError("Digest content is empty")

    if not re.search(r"^## \d+\.", md, re.MULTILINE):
        raise ValueError("No article sections found")

    if "[[" in md or "]]" in md:
        raise ValueError("Possible broken markdown link brackets")

    # Optional: check summaries aren't all missing
    if md.count("**Summary:**") == 0:
        raise ValueError("No summaries detected")

    return True
