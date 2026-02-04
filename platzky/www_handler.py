import typing as t
import urllib.parse

from flask import redirect, request


def _matches_known_domain(netloc: str, known_domains: set[str]) -> bool:
    """Check if the request's netloc (without www.) matches any known domain (without www.)."""
    bare = netloc.removeprefix("www.")
    return bare in known_domains


def _get_bare_domains(domains: t.Iterable[str]) -> set[str]:
    """Strip www. prefix from configured domains to get base domains."""
    return {d.removeprefix("www.") for d in domains}


def redirect_nonwww_to_www(known_domains: set[str]):
    """Redirect non-www requests to www, only for known domains."""
    urlparts = urllib.parse.urlparse(request.url)
    if not urlparts.netloc.startswith("www.") and _matches_known_domain(
        urlparts.netloc, known_domains
    ):
        urlparts = urlparts._replace(netloc=f"www.{urlparts.netloc}")
        url = urllib.parse.urlunparse(urlparts)
        return redirect(url, code=301)


def redirect_www_to_nonwww(known_domains: set[str]):
    """Redirect www requests to non-www, only for known domains."""
    urlparts = urllib.parse.urlparse(request.url)
    if urlparts.netloc.startswith("www.") and _matches_known_domain(
        urlparts.netloc, known_domains
    ):
        urlparts = urlparts._replace(netloc=urlparts.netloc.removeprefix("www."))
        url = urllib.parse.urlunparse(urlparts)
        return redirect(url, code=302)
