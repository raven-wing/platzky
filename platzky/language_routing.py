"""Locale resolution from the request host and path.

Every configured language has exactly one URL: the default language at the root of the main
host, a language with its own ``domain`` at the root of that domain, and any other language
under ``/<code>/`` on the main host.
"""

from collections.abc import Mapping
from dataclasses import dataclass

LANG_CODE_ARG = "lang_code"
RESERVED_PATH_SEGMENTS = frozenset({"lang", "static", "admin", "login", "health", "api"})


@dataclass(frozen=True)
class SiteLanguages:
    """The configured languages as URL routing sees them.

    Attributes:
        domains: Language codes mapped to their own domain, or None for a language without one.
        default: Code of the language served at the root of the main host.
    """

    domains: Mapping[str, str | None]
    default: str

    @property
    def path_languages(self) -> tuple[str, ...]:
        """Codes of the non-default languages without a domain, served under ``/<code>/``."""
        return tuple(
            code for code, domain in self.domains.items() if domain is None and code != self.default
        )


def language_for_host(languages: SiteLanguages, host: str) -> str:
    """Return the language whose ``domain`` matches ``host``, or the default language.

    A domain matches only the host exactly as written, ``www.`` included. A domain with an
    explicit port must match the host's port exactly; a domain without one matches regardless
    of port (e.g. behind a proxy that forwards on a non-standard port). An exact match wins
    over a domain without a port, whatever their order.

    Args:
        languages: The site's languages.
        host: Request host, optionally with a port.

    Returns:
        The code of the language whose domain is ``host``; the default language when no
        language claims it.
    """
    host_without_port = host.split(":", 1)[0]
    domains = {code: domain for code, domain in languages.domains.items() if domain is not None}
    exact = next((code for code, domain in domains.items() if domain == host), None)
    return exact or next(
        (
            code
            for code, domain in domains.items()
            if ":" not in domain and domain == host_without_port
        ),
        languages.default,
    )


def dedicated_language(languages: SiteLanguages, host: str) -> str | None:
    """Return the non-default language whose own domain is ``host``, if any."""
    code = language_for_host(languages, host)
    return code if code != languages.default else None


def resolve_locale(languages: SiteLanguages, host: str, path: str) -> str:
    """Return the language a request is served in.

    Args:
        languages: The site's languages.
        host: Request host.
        path: Request path.

    Returns:
        The language whose own domain is ``host``; else the path language whose prefix
        ``path`` starts with; else the default language.
    """
    if code := dedicated_language(languages, host):
        return code
    for lang in languages.path_languages:
        if path == f"/{lang}" or path.startswith(f"/{lang}/"):
            return lang
    return languages.default


def served_languages(languages: SiteLanguages, host: str) -> dict[str, str]:
    """Map each language served on ``host`` to its URL prefix.

    Args:
        languages: The site's languages.
        host: Request host.

    Returns:
        ``{code: ""}`` on a language's own domain; otherwise the default language with an
        empty prefix plus every path language with ``"/<code>"``.
    """
    if code := dedicated_language(languages, host):
        return {code: ""}
    return {languages.default: "", **{lang: f"/{lang}" for lang in languages.path_languages}}


def language_url(
    languages: SiteLanguages, lang: str, scheme: str, host: str, path: str = "/"
) -> str:
    """Return the absolute URL of a page in a language, valid from any host.

    Args:
        languages: The site's languages.
        lang: Language code to link to.
        scheme: URL scheme of the current request.
        host: Host of the current request.
        path: Path of the page without any language prefix; the home page by default.

    Returns:
        ``path`` on the language's own domain for a domain language. For the default and path
        languages, ``path`` or ``/<code>path`` on the current host, or on the default
        language's domain when the current host belongs to another language.
    """
    domain = languages.domains.get(lang)
    if domain and lang != languages.default:
        return f"{scheme}://{domain}{path}"
    default_domain = languages.domains.get(languages.default)
    if default_domain and dedicated_language(languages, host):
        host = default_domain
    prefix = "" if lang == languages.default else f"/{lang}"
    return f"{scheme}://{host}{prefix}{path}"
