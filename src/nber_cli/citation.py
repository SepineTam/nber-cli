#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam (谭淞)
# @Email  : sepinetam@gmail.com
# @File   : citation.py

"""Plain-text bibliography entries for NBER working papers."""

from __future__ import annotations

import re
from datetime import date

from .core.models import NBER
from .utils.formatters import paper_id_str

FORMAT_ALIASES = {"bibtex": "bib", "gbt7714": "gb"}
FORMAT_LABELS = {
    "bib": "BibTeX", "apa": "APA 7th", "mla": "MLA 9th",
    "harvard": "Harvard", "chicago": "Chicago 18th", "gb": "GB/T 7714—2025",
}
FORMATS = tuple(FORMAT_LABELS) + tuple(FORMAT_ALIASES)
_INSTITUTION = "National Bureau of Economic Research"
_PARTICLES = {"de", "del", "della", "der", "di", "du", "la", "le", "van", "von", "den", "da", "dos"}


def _name(author: str) -> tuple[str, str]:
    """Accept 'family, given' and common natural-order names with particles."""
    if "," in author:
        family, given = author.split(",", 1)
        return family.strip(), given.strip()
    parts = author.split()
    if not parts:
        return "Unknown author", ""
    start = len(parts) - 1
    while start > 0 and parts[start - 1].lower() in _PARTICLES:
        start -= 1
    return " ".join(parts[start:]), " ".join(parts[:start])


def _initials(given: str, *, dots: bool = True) -> str:
    words = given.split()
    return (" " if dots else "").join(
        "-".join(part[0].upper() + ("." if dots else "") for part in word.split("-") if part)
        for word in words
    )


def _inverted(author: str) -> str:
    family, given = _name(author)
    return f"{family}, {_initials(given)}" if given else family


def _join(
    authors: list[str],
    conjunction: str = "and",
    serial: bool = True,
    two_author_comma: bool = False,
) -> str:
    if len(authors) < 2:
        return authors[0] if authors else "Unknown author"
    if len(authors) == 2:
        separator = f", {conjunction} " if two_author_comma else f" {conjunction} "
        return f"{authors[0]}{separator}{authors[1]}"
    return f"{', '.join(authors[:-1])}{',' if serial else ''} {conjunction} {authors[-1]}"


def _escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "&": r"\&",
        "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in value)


def format_citation(paper: NBER, style: str = "bib", *, accessed: date | None = None) -> str:
    style = FORMAT_ALIASES.get(style, style)
    if style not in FORMAT_LABELS:
        raise ValueError(f"unsupported citation format: {style}")
    title = " ".join(paper.title.split())
    if not title:
        raise ValueError("paper title is missing")
    authors = [" ".join(author.split()) for author in paper.authors if author.strip()]
    year_match = re.match(r"\d{4}(?=$|[-/\s])", paper.date.strip())
    year = year_match.group() if year_match else "n.d."
    code = paper_id_str(paper)
    url = paper.url or f"https://www.nber.org/papers/{code}"
    number = str(paper.paper_id)
    series = "NBER Working Paper" if paper.series == "w" else "NBER Historical Working Paper"
    initials = [_inverted(author) for author in authors]
    end_title = title if title.endswith((".", "?", "!")) else title + "."

    if style == "bib":
        names = []
        for author in authors:
            family, given = _name(author)
            names.append(f"{family}, {given}" if given else family)
        fields = {
            "title": title, "author": " and ".join(names), "institution": _INSTITUTION,
            "type": "Working Paper" if paper.series == "w" else "Historical Working Paper",
            "number": number, "year": year if year_match else "", "url": url,
        }
        lines = [f"  {key} = {{{_escape(value)}}}" for key, value in fields.items() if value]
        return f"@techreport{{nber{code},\n" + ",\n".join(lines) + "\n}"
    if style == "apa":
        # APA lists the first 19 and the last author for more than 20 authors.
        author_line = _join(initials, "&", two_author_comma=True) if len(initials) <= 20 else ", ".join(initials[:19]) + ", … " + initials[-1]
        return f"{author_line} ({year}). {title} ({series} No. {number}). {_INSTITUTION}. {url}"
    if style == "mla":
        family, given = _name(authors[0]) if authors else ("Unknown author", "")
        author_line = f"{family}, {given}" if given else family
        if len(authors) == 2:
            second_family, second_given = _name(authors[1])
            author_line += f", and {second_given} {second_family}".replace("and  ", "and ")
        elif len(authors) > 2:
            author_line += ", et al."
        return f"{author_line.rstrip('.')}. “{end_title}” {series}, no. {number}, {_INSTITUTION}, {year}, {url}."
    if style == "harvard":
        return f"{_join(initials, serial=False)} ({year}) ‘{title}’, {series}, no. {number}. {_INSTITUTION}. Available at: {url}"
    if style == "chicago":
        names = []
        for index, author in enumerate(authors):
            family, given = _name(author)
            names.append(f"{family}, {given}" if index == 0 and given else " ".join(filter(None, (given, family))))
        return f"{_join(names, two_author_comma=True).rstrip('.')}. {year}. “{end_title}” {series} {number}. {_INSTITUTION}. {url}."
    gb_names = []
    for author in authors[:3]:
        family, given = _name(author)
        gb_names.append(f"{family.upper()} {_initials(given, dots=False)}".strip())
    author_line = ", ".join(gb_names) or "Unknown author"
    if len(authors) > 3:
        author_line += ", et al"
    return f"{author_line}. {title}: {series} {number}[R/OL]. {_INSTITUTION}, {year}[{(accessed or date.today()).isoformat()}]. {url}."
