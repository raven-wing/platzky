"""Locale resolution from the request host and path.

Every configured language has exactly one URL: the default language at the root of the main
host, a language with its own ``domain`` at the root of that domain, and any other language
under ``/<code>/`` on the main host.
"""

import typing as t

if t.TYPE_CHECKING:
    from platzky.config import Config

LANG_CODE_ARG = "lang_code"
RESERVED_PATH_SEGMENTS = frozenset({"lang", "static", "admin", "login", "health", "api"})


def language_for_host(config: "Config", host: str) -> str:
    """Return the language whose ``domain`` matches ``host``, or the default language.

    A domain matches only the host exactly as written, ``www.`` included. A domain with an
    explicit port must match the host's port exactly; a domain without one matches regardless
    of port (e.g. behind a proxy that forwards on a non-standard port). An exact match wins
    over a domain without a port, whatever their order.

    Args:
        config: Application configuration.
        host: Request host, optionally with a port.

    Returns:
        The code of the language whose domain is ``host``; the default language when no
        language claims it.
    """
    host_without_port = host.split(":", 1)[0]
    domains = {
        code: language.domain
        for code, language in config.languages.items()
        if language.domain is not None
    }
    exact = next((code for code, domain in domains.items() if domain == host), None)
    return exact or next(
        (
            code
            for code, domain in domains.items()
            if ":" not in domain and domain == host_without_port
        ),
        config.default_language,
    )


def dedicated_language(config: "Config", host: str) -> str | None:
    """Return the non-default language whose own domain is ``host``, if any."""
    code = language_for_host(config, host)
    return code if code != config.default_language else None


def resolve_locale(config: "Config", host: str, path: str) -> str:
    """Return the language a request is served in.

    Args:
        config: Application configuration.
        host: Request host.
        path: Request path.

    Returns:
        The language whose own domain is ``host``; else the path language whose prefix
        ``path`` starts with; else the default language.
    """
    if code := dedicated_language(config, host):
        return code
    for lang in config.path_languages:
        if path == f"/{lang}" or path.startswith(f"/{lang}/"):
            return lang
    return config.default_language


def served_languages(config: "Config", host: str) -> dict[str, str]:
    """Map each language served on ``host`` to its URL prefix.

    Args:
        config: Application configuration.
        host: Request host.

    Returns:
        ``{code: ""}`` on a language's own domain; otherwise the default language with an
        empty prefix plus every path language with ``"/<code>"``.
    """
    if code := dedicated_language(config, host):
        return {code: ""}
    return {config.default_language: "", **{lang: f"/{lang}" for lang in config.path_languages}}


def language_url(config: "Config", lang: str, scheme: str, host: str, path: str = "/") -> str:
    """Return the absolute URL of a page in a language, valid from any host.

    Args:
        config: Application configuration.
        lang: Language code to link to.
        scheme: URL scheme of the current request.
        host: Host of the current request.
        path: Path of the page without any language prefix; the home page by default.

    Returns:
        ``path`` on the language's own domain for a domain language. For the default and path
        languages, ``path`` or ``/<code>path`` on the current host, or on the default
        language's domain when the current host belongs to another language.
    """
    languages = config.languages
    language = languages.get(lang)
    if language and language.domain and lang != config.default_language:
        return f"{scheme}://{language.domain}{path}"
    default = languages.get(config.default_language)
    if default and default.domain and dedicated_language(config, host):
        host = default.domain
    prefix = "" if lang == config.default_language else f"/{lang}"
    return f"{scheme}://{host}{prefix}{path}"
