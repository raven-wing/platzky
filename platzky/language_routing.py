"""Locale resolution from the request host and path.

Every configured language has exactly one URL: the default language at the root of the main
host, a language with its own ``domain`` at the root of that domain, and any other language
under ``/<code>/`` on the main host.
"""

import typing as t
from collections.abc import Mapping
from dataclasses import dataclass

LANG_CODE_ARG = "lang_code"
RESERVED_PATH_SEGMENTS = frozenset({"lang", "static", "admin", "login", "health", "api"})

_MULTILANG_ATTR = "platzky_multilang"
View = t.TypeVar("View", bound=t.Callable[..., t.Any])


def multilang(view: View) -> View:
    """Serve a view in every language: also under ``/<code>/`` for each domainless language.

    Place it below the ``route`` decorator. While a request is in a domainless language, ``url_for``
    builds the view's URL under that language's prefix.

    Args:
        view: The view function to mark.

    Returns:
        The same view, marked.
    """
    setattr(view, _MULTILANG_ATTR, True)
    return view


def is_multilang(view: t.Callable[..., t.Any]) -> bool:
    """Return whether ``view`` was marked with ``multilang``."""
    return getattr(view, _MULTILANG_ATTR, False)


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
    def domainless_languages(self) -> tuple[str, ...]:
        """Codes of the languages without their own domain, served under ``/<lang_code>/``.

        The default language is never one of them: it owns the root of the main host, even
        when no ``domain`` is configured for it.
        """
        return tuple(
            lang_code
            for lang_code, domain in self.domains.items()
            if domain is None and lang_code != self.default
        )

    @property
    def domainful_languages(self) -> tuple[str, ...]:
        """Codes of the languages served at the root of a host, never under ``/<lang_code>/``.

        These are every language with its own domain, and the default language, which owns
        the main host even when no ``domain`` is configured for it. Together with
        ``domainless_languages`` they cover every configured language.
        """
        return tuple(
            lang_code
            for lang_code in dict.fromkeys([self.default, *self.domains])
            if lang_code not in self.domainless_languages
        )


def any_converter(lang_codes: t.Iterable[str]) -> str:
    """Return a URL converter matching exactly the given codes, e.g. ``any('pl', 'uk')``."""
    return "any(" + ", ".join(f"'{lang_code}'" for lang_code in lang_codes) + ")"


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
    domains = {
        lang_code: domain for lang_code, domain in languages.domains.items() if domain is not None
    }
    exact = next((lang_code for lang_code, domain in domains.items() if domain == host), None)
    return exact or next(
        (
            lang_code
            for lang_code, domain in domains.items()
            if ":" not in domain and domain == host_without_port
        ),
        languages.default,
    )


def dedicated_language(languages: SiteLanguages, host: str) -> str | None:
    """Return the non-default language whose own domain is ``host``, if any."""
    lang_code = language_for_host(languages, host)
    return lang_code if lang_code != languages.default else None


def resolve_locale(languages: SiteLanguages, host: str, path: str) -> str:
    """Return the language a request is served in.

    Args:
        languages: The site's languages.
        host: Request host.
        path: Request path.

    Returns:
        The language whose own domain is ``host``; else the domainless language whose prefix
        ``path`` starts with; else the default language.
    """
    if lang_code := dedicated_language(languages, host):
        return lang_code
    for lang in languages.domainless_languages:
        if path == f"/{lang}" or path.startswith(f"/{lang}/"):
            return lang
    return languages.default


def served_languages(languages: SiteLanguages, host: str) -> dict[str, str]:
    """Map each language served on ``host`` to its URL prefix.

    Args:
        languages: The site's languages.
        host: Request host.

    Returns:
        ``{lang_code: ""}`` on a language's own domain; otherwise the default language with an
        empty prefix plus every domainless language with ``"/<code>"``.
    """
    if lang_code := dedicated_language(languages, host):
        return {lang_code: ""}
    return {languages.default: "", **{lang: f"/{lang}" for lang in languages.domainless_languages}}


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
