#!/usr/bin/env python3
"""Cigarr-briefen — automatisk hämtning och filtrering av cigarrnyheter.

Byggd i samma anda som Fotbollsbriefens update.py: hämtar RSS/Atom-flöden
och Google News-sökningar, filtrerar bort skräp/reklam, slår ihop samma
nyhet från flera källor och skriver resultatet till news.json som sidan
sedan läser via JavaScript.
"""
from __future__ import annotations

import datetime as dt
import email.utils
import html
import json
import re
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "sources.json"
OUTPUT_PATH = ROOT / "news.json"
USER_AGENT = "Mozilla/5.0 CigarrBriefen/Nyhetsbot-1.0"
NOW = dt.datetime.now(dt.timezone.utc)

# ---------------------------------------------------------------------------
# Filter: skräp, reklam och innehåll som inte hör hemma i ett seriöst nyhetsflöde
# ---------------------------------------------------------------------------
JUNK_RE = re.compile(
    r"\b(shop now|buy now|coupon|promo code|discount code|% off|clearance|"
    r"sale ends|giveaway|sweepstakes|subscribe now|newsletter signup|"
    r"sponsored content|advertisement|affiliate|best deals?|deal of the day|"
    r"free shipping)\b",
    re.I,
)

# Filtrerar bort träffar som råkar innehålla ordet "cigar"/"cigarr" men som
# inte handlar om premiumcigarrer (cigaretter, vejp, uttryck, tecknat etc.)
OFF_TOPIC_RE = re.compile(
    r"\b(e-cigarette|e-cigarettes|vape|vaping|cigar[- ]box guitar|"
    r"close but no cigar|cigar[- ]shaped|cartoon|comic strip|cigar lounge chair|"
    r"cigarettes? tax(?!.{0,25}cigar)|crypto|nft)\b",
    re.I,
)

NEWS_SIGNAL_RE = re.compile(
    r"\b(launch|launches|launched|release|releases|released|unveil|unveils|"
    r"unveiled|debut|debuts|acquire|acquires|acquired|acquisition|recall|"
    r"recalled|regulation|regulations|tariff|tariffs|tax|taxes|fda|lawsuit|"
    r"court|ruling|verdict|price increase|shortage|factory|rolling|humidor|"
    r"blend|limited edition|award|awarded|named|rating|score|distributor|"
    r"import|export|license|licence|nytt|lanserar|lansering|tillstånd|skatt|"
    r"tull|åtal|dom|rättegång|återkallar|prishöjning|tilldelas|utmärkelse)\b",
    re.I,
)

LOW_VALUE_TITLE_RE = re.compile(
    r"\b(top \d+ cigars? (you|to)|best cigars? (of|for) (the )?(week|month)|"
    r"everything you need to know|what we learned|round-?up|"
    r"click here|you won'?t believe)\b",
    re.I,
)

CLICKBAIT_RE = re.compile(
    r"\b(iconic|stunning|amazing|incredible|shocking|game-?changing|"
    r"could change everything)\b",
    re.I,
)

MARKETING_RE = re.compile(
    r"\b(shop our|visit our store|join our club|membership offer|"
    r"exclusive offer|limited time offer)\b",
    re.I,
)

# Positive relevance check. Some trusted cigar publishers (Cigar Aficionado, Cigar Coop)
# run broader lifestyle content — golf resorts, cars, restaurant reviews — through the same
# RSS feed. OFF_TOPIC_RE only catches things that are wrongly *about* cigars (vaping, cigar-box
# guitars); it doesn't catch things that aren't about cigars at all. Require at least one
# cigar-domain term anywhere in title+description instead.
CIGAR_TOPIC_RE = re.compile(
    r"\b(cigar|cigars|cigarr|cigarrer|cigarrer[a-zåäö]*|tobacco|tobak|wrapper|binder|filler|"
    r"humidor|vitola|vitolas|blend|blends|torcedor|puro|puros|habano|maduro|"
    r"corojo|connecticut|broadleaf|criollo|leaf|leaves|estelí|jalapa|jamastran|"
    r"danlí|plantation|harvest|fermentation|box[- ]press|robusto|toro|churchill|"
    r"lancero|belicoso|torpedo|piramide|perfecto|smoke shop|tobacconist|pca trade show)\b",
    re.I,
)

TRUSTED_PUBLISHERS = {
    "halfwheel", "Cigar Journal", "Cigar Snob Magazine", "Cigar Aficionado",
    "Cigarrvärlden", "Cigar Coop",
}

BLOCKED_PUBLISHERS: set[str] = set()

SOURCE_ALIASES = {
    "Halfwheel": "halfwheel",
    "HalfWheel": "halfwheel",
    "cigarjournal.com": "Cigar Journal",
    "Cigar Journal - The Magazine for Fine Smoke & Savoir Vivre": "Cigar Journal",
}

SOURCE_RANK = {
    "halfwheel": 100,
    "Cigarrvärlden": 96,
    "Cigar Journal": 92,
    "Cigar Aficionado": 90,
    "Cigar Coop": 80,
    "Cigar Snob Magazine": 75,
}

DOMAIN_RE = re.compile(
    r"(?:\s|^)(?:[A-Za-z0-9-]+\.)+(?:com|net|org|co\.uk|se|dk|no)\b",
    re.I,
)

SOURCE_RESIDUE_RE = re.compile(
    r"\b(?:halfwheel|Cigar Journal|Cigar Aficionado|Cigar Snob Magazine|"
    r"Cigar Coop|Cigarrvärlden|Official Site|Official Website|Latest News|News)\b\s*$",
    re.I,
)

STOPWORDS = {
    "the", "and", "for", "from", "with", "into", "over", "after", "before",
    "amid", "about", "near", "close", "news", "official", "cigar", "cigars",
    "latest", "today", "why", "what", "how", "when", "this", "that",
}

SWEDISH_WORDS = {"och", "att", "en", "ett", "med", "om", "eller", "men", "hos", "till", "från", "av", "på", "i"}

NON_ENGLISH_WORDS = {
    "della", "degli", "delle", "alla", "allo", "agli", "nella", "nello",
    "avec", "pour", "chez", "dans", "entraîneur", "entraineur",
    "fichaje", "fichajes", "entrenador", "llega", "llegan",
    "spieler", "vertrag", "wechsel", "mannschaft",
}
NON_ENGLISH_FUNCTION_WORDS = {
    "della", "degli", "delle", "nella", "nello", "agli", "allo",
    "avec", "pour", "chez", "dans", "des", "les",
    "para", "desde", "hasta", "tambien", "también",
    "der", "die", "das", "ein", "eine", "einen", "einem", "einer", "und", "für",
}


def fetch(url: str, timeout: int = 22) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(
        request,
        timeout=timeout,
        context=ssl.create_default_context(),
    ) as response:
        return response.read()


def clean_text(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    return re.sub(r"\s+", " ", value).strip()


def parse_date(value: str) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    except Exception:
        try:
            return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
        except Exception:
            return None


def normalize(value: str) -> str:
    value = re.sub(r"[^a-zåäö0-9 ]", " ", value.lower())
    return re.sub(r"\s+", " ", value).strip()


def significant_words(value: str) -> set[str]:
    return {
        word for word in re.findall(r"[a-zåäö0-9]+", normalize(value))
        if len(word) >= 4 and word not in STOPWORDS
    }


def similarity(first: str, second: str) -> float:
    if not first or not second:
        return 0.0
    return SequenceMatcher(None, normalize(first), normalize(second)).ratio()


def local_name(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def child_text(node: ET.Element, names: list[str]) -> str:
    for child in node:
        if local_name(child.tag) in names and child.text and child.text.strip():
            return child.text.strip()
    return ""


def entry_link(node: ET.Element) -> str:
    """RSS: <link>url</link>. Atom: <link href="url" rel="alternate"/> (possibly flera)."""
    atom_links: list[tuple[str, str]] = []
    for child in node:
        if local_name(child.tag) != "link":
            continue
        href = child.attrib.get("href")
        if href:
            atom_links.append((child.attrib.get("rel", "alternate"), href))
        elif child.text and child.text.strip():
            return child.text.strip()
    for rel, href in atom_links:
        if rel == "alternate":
            return href
    return atom_links[0][1] if atom_links else ""


def entry_description(node: ET.Element) -> str:
    for names in (["description"], ["summary"], ["encoded"], ["content"]):
        text = child_text(node, names)
        if text:
            return text
    return ""


def entry_date(node: ET.Element) -> str:
    return child_text(node, ["pubDate", "published", "updated", "date"])


def google_news_url(query: str, hl: str, gl: str, ceid: str, days: int) -> str:
    full_query = f"{query} when:{days}d"
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": full_query, "hl": hl, "gl": gl, "ceid": ceid}
    )


def split_google_title(raw_title: str) -> tuple[str, str | None]:
    if " - " not in raw_title:
        return raw_title.strip(), None
    title, publisher = raw_title.rsplit(" - ", 1)
    return title.strip(), publisher.strip()


def normalized_source(name: str) -> str:
    name = (name or "").strip()
    return SOURCE_ALIASES.get(name, name)


def clean_headline(title: str) -> str:
    title = clean_text(title)
    title = re.sub(
        r"\s*[\|\-–—]\s*(Official Site|Official Website|News|Latest News)\s*$",
        "",
        title,
        flags=re.I,
    )
    return re.sub(r"\s+", " ", title).strip(" .-|–—")


def clean_excerpt(summary: str, title: str) -> str:
    summary = clean_text(summary)
    summary = DOMAIN_RE.sub(" ", summary)
    summary = SOURCE_RESIDUE_RE.sub("", summary).strip(" .-|–—")
    if similarity(title, summary) >= 0.86:
        return ""

    sentences: list[str] = []
    seen: set[str] = set()
    for sentence in re.split(r"(?<=[.!?])\s+", summary):
        sentence = clean_text(sentence)
        if len(sentence) < 30 or similarity(title, sentence) >= 0.86:
            continue
        key = normalize(sentence)
        if not key or key in seen:
            continue
        seen.add(key)
        sentences.append(sentence)
        if len(sentences) >= 3:
            break
    return " ".join(sentences)[:850]


def categories(title: str, publisher: str = "") -> list[str]:
    lowered = title.lower()
    output: list[str] = []

    if publisher == "Cigarrvärlden":
        output.append("Sverige")

    pairs = [
        ("Kuba", r"\bcuba|cuban|habanos|havana\b"),
        ("Nicaragua", r"\bnicaragua|este[l]í?\b"),
        ("Dominikanska republiken", r"\bdominican|dominikansk|santiago de los caballeros\b"),
        ("Honduras", r"\bhonduras|danl[ií]\b"),
        ("Nya utgåvor", r"\blaunch|release[sd]?|debut|new blend|limited edition|unveil"),
        ("Reglering", r"\bfda|regulation|tariff|tax(es)?|lag(stiftning)?|licens|tull|åtal|rättegång"),
        ("Boutique", r"\bboutique\b"),
        ("Event", r"\bpca|trade show|imex|festival|expo\b"),
        ("Test & betyg", r"\breview|rating|score|betyg\b"),
    ]
    for category, pattern in pairs:
        if re.search(pattern, lowered):
            output.append(category)

    return output or ["Nyheter"]


def source_status(source: str, source_count: int) -> str:
    if source_count >= 2:
        return "Bekräftad av flera källor"
    if source in TRUSTED_PUBLISHERS:
        return "Trovärdig källa"
    return "Rapporterad"


def source_score(name: str, configured_priority: int) -> int:
    name = normalized_source(name)
    if name in SOURCE_RANK:
        return SOURCE_RANK[name]
    return configured_priority


def rank_sources(sources: list[dict[str, str]]) -> list[dict[str, str]]:
    unique: dict[str, dict[str, str]] = {}
    for source in sources:
        name = normalized_source(source.get("name", ""))
        if not name or name in BLOCKED_PUBLISHERS:
            continue
        if name not in unique:
            unique[name] = {"name": name, "url": source.get("url", "")}
    return sorted(
        unique.values(),
        key=lambda source: source_score(source["name"], 40),
        reverse=True,
    )


def quality_score(title: str, description: str, publisher: str, configured_priority: int) -> int:
    combined = f"{title} {description}"
    score = source_score(publisher, configured_priority)
    if publisher in TRUSTED_PUBLISHERS:
        score += 25
    if NEWS_SIGNAL_RE.search(combined):
        score += 20
    if JUNK_RE.search(combined):
        score -= 150
    if OFF_TOPIC_RE.search(combined):
        score -= 200
    if LOW_VALUE_TITLE_RE.search(title):
        score -= 100
    if MARKETING_RE.search(combined):
        score -= 150
    if CLICKBAIT_RE.search(title) and publisher not in TRUSTED_PUBLISHERS:
        score -= 70
    if publisher not in TRUSTED_PUBLISHERS:
        score -= 20
    if len(clean_text(description)) < 40:
        score -= 15
    return score


def is_acceptable_language(title: str, description: str = "") -> bool:
    text = clean_text(f"{title} {description}").lower()
    words = re.findall(r"[a-zåäöà-öø-ÿ]+", text)

    swedish_hits = sum(word in SWEDISH_WORDS for word in words)
    if swedish_hits >= 2:
        return True

    strong_hits = sum(word in NON_ENGLISH_WORDS for word in words)
    function_hits = sum(word in NON_ENGLISH_FUNCTION_WORDS for word in words)
    if strong_hits >= 1 or function_hits >= 3:
        return False
    return True


ARTICLE_BLOCKLIST_RE = re.compile(
    r"\b(cookie|privacy|newsletter|subscribe|sign up|advertisement|"
    r"related articles?|read more|follow us|share this article|"
    r"all rights reserved|terms and conditions|accept all|manage preferences)\b",
    re.I,
)
ARTICLE_BOILERPLATE_RE = re.compile(
    r"^(home|cigars?|news|latest|menu|search|shop|skip to content)$",
    re.I,
)


class ParagraphExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._inside_p = False
        self._inside_ignored = 0
        self._buffer: list[str] = []
        self.paragraphs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "nav", "footer", "header", "aside", "form", "noscript"}:
            self._inside_ignored += 1
            return
        if self._inside_ignored:
            return
        if tag == "p":
            self._inside_p = True
            self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "nav", "footer", "header", "aside", "form", "noscript"}:
            if self._inside_ignored:
                self._inside_ignored -= 1
            return
        if self._inside_ignored:
            return
        if tag == "p" and self._inside_p:
            text = clean_text(" ".join(self._buffer))
            if text:
                self.paragraphs.append(text)
            self._inside_p = False
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._inside_p and not self._inside_ignored:
            self._buffer.append(data)


class MetaExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "meta":
            return
        attr = {k.lower(): (v or "") for k, v in attrs}
        key = (attr.get("property") or attr.get("name") or "").lower()
        content = attr.get("content", "").strip()
        if key and content and key not in self.meta:
            self.meta[key] = content


GOOGLE_OWNED_DOMAIN_RE = re.compile(
    r"^(?:[\w-]+\.)*(?:google\.[a-z.]+|googleusercontent\.com|gstatic\.com|"
    r"googleapis\.com|googletagmanager\.com|google-analytics\.com|doubleclick\.net|"
    r"googlesyndication\.com|gvt1\.com|ggpht\.com)$",
    re.I,
)
IMAGE_EXT_RE = re.compile(r"\.(?:png|jpe?g|gif|webp|svg|ico|bmp)(?:[?#]|$)", re.I)


def is_real_article_href(href: str) -> bool:
    """True if href looks like an actual external article, not a Google-owned asset
    (image CDN, analytics, static resources) or an image file."""
    try:
        host = urllib.parse.urlparse(href).netloc.split(":")[0]
    except Exception:
        return False
    if not host or GOOGLE_OWNED_DOMAIN_RE.match(host):
        return False
    if IMAGE_EXT_RE.search(href):
        return False
    return True


def resolve_article_url(url: str) -> str:
    if "news.google.com" not in url:
        return url
    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=15, context=ssl.create_default_context()) as response:
            final = response.geturl()
            if "news.google.com" not in final:
                return final
            page = response.read().decode("utf-8", errors="replace")
    except Exception:
        return url

    for pattern in (
        r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\'](https?://[^"\']+)',
        r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\'](https?://[^"\']+)',
        r'data-n-au=["\'](https?://[^"\']+)',
    ):
        match = re.search(pattern, page, re.I)
        if match and is_real_article_href(match.group(1)):
            return match.group(1)

    # Fall back to scanning every href on the page in order and taking the first one
    # that isn't a Google-owned asset (image CDN, analytics, static resources, etc.).
    for match in re.finditer(r'href=["\'](https?://[^"\']+)', page):
        candidate = match.group(1)
        if is_real_article_href(candidate):
            return candidate

    return url


def usable_article_paragraph(text: str, title: str) -> bool:
    text = clean_text(text)
    if len(text) < 70 or len(text) > 900:
        return False
    if ARTICLE_BLOCKLIST_RE.search(text):
        return False
    if ARTICLE_BOILERPLATE_RE.fullmatch(text):
        return False
    if similarity(title, text) >= 0.86:
        return False
    if len(text.split()) < 12:
        return False
    if text.count("|") >= 2 or text.count("›") >= 2:
        return False
    return True


def article_meta_description(meta: dict[str, str], title: str) -> str:
    candidate = clean_text(
        meta.get("og:description") or meta.get("twitter:description") or meta.get("description") or ""
    )
    if not candidate:
        return ""
    candidate = SOURCE_RESIDUE_RE.sub("", candidate).strip(" .-|–—")
    if len(candidate) < 60 or similarity(title, candidate) >= 0.9 or ARTICLE_BLOCKLIST_RE.search(candidate):
        return ""
    return candidate[:500]


def extract_article_metadata(article_url: str, title: str) -> tuple[str, str]:
    try:
        if "news.google.com" in article_url:
            return "", ""

        html_bytes = fetch(article_url, timeout=15)
        encoding = "utf-8"
        match = re.search(br'charset=["\']?\s*([A-Za-z0-9._-]+)', html_bytes[:5000], re.I)
        if match:
            encoding = match.group(1).decode("ascii", errors="ignore") or "utf-8"
        page = html_bytes.decode(encoding, errors="replace")

        meta_parser = MetaExtractor()
        meta_parser.feed(page)
        og_image = meta_parser.meta.get("og:image") or ""

        meta_summary = article_meta_description(meta_parser.meta, title)
        if meta_summary:
            return meta_summary, og_image

        parser = ParagraphExtractor()
        parser.feed(page)

        selected: list[str] = []
        seen: set[str] = set()
        for paragraph in parser.paragraphs:
            paragraph = clean_text(paragraph)
            key = normalize(paragraph)
            if not key or key in seen:
                continue
            seen.add(key)
            if not usable_article_paragraph(paragraph, title):
                continue
            selected.append(paragraph)
            if len(" ".join(selected)) >= 220 or len(selected) >= 2:
                break

        return " ".join(selected)[:850], og_image
    except Exception:
        return "", ""


def rss_only_summary(title: str, rss_description: str) -> str:
    rss_summary = clean_excerpt(rss_description, title)
    if rss_summary and len(rss_summary) >= 60:
        return rss_summary

    fragment = clean_text(rss_description)
    fragment = DOMAIN_RE.sub(" ", fragment)
    fragment = SOURCE_RESIDUE_RE.sub("", fragment).strip(" .-|–—")
    if len(fragment) >= 40 and similarity(title, fragment) < 0.86 and not ARTICLE_BLOCKLIST_RE.search(fragment):
        return fragment[:500]
    return ""


def parse_feed(xml_bytes: bytes, source: dict[str, Any], cutoff: dt.datetime) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_bytes)
    output: list[dict[str, Any]] = []

    entries = [el for el in root.iter() if local_name(el.tag) in ("item", "entry")]

    for node in entries:
        raw_title = clean_text(child_text(node, ["title"]))
        link = clean_text(entry_link(node))
        published = parse_date(entry_date(node))
        raw_description = entry_description(node)

        if not raw_title or not link or not published or published < cutoff:
            continue

        if source["type"] == "google":
            title, publisher = split_google_title(raw_title)
            publisher = normalized_source(publisher or source["name"])
        else:
            title = raw_title
            publisher = normalized_source(source["name"])

        title = clean_headline(title)
        combined = f"{title} {raw_description}"

        # Google News' <description> for a result is essentially just the title again
        # plus the publisher name — not a real excerpt. For sources like "Cigar Aficionado"
        # or "Cigar Coop", the publisher name alone contains "cigar", so testing it against
        # CIGAR_TOPIC_RE would always pass regardless of what the article is actually about
        # (this is how golf-resort and car-rally lifestyle pieces slipped through). Direct
        # RSS feeds carry a genuine excerpt, so keep testing title+description for those.
        topic_check_text = title if source["type"] == "google" else combined

        if not is_acceptable_language(title, raw_description):
            continue
        if publisher in BLOCKED_PUBLISHERS:
            continue
        if JUNK_RE.search(combined) or OFF_TOPIC_RE.search(combined) or LOW_VALUE_TITLE_RE.search(title):
            continue
        if MARKETING_RE.search(combined):
            continue
        if not CIGAR_TOPIC_RE.search(topic_check_text):
            continue

        score = quality_score(title, raw_description, publisher, int(source.get("priority", 40)))
        if score < 50:
            continue

        summary = rss_only_summary(title, raw_description)
        cats = categories(title, publisher)

        output.append({
            "published_at": published.isoformat(),
            "updated_at": published.isoformat(),
            "title": title,
            "summary": summary,
            "category": cats,
            "status": source_status(publisher, 1),
            "image": "",
            "source_priority": score,
            "sources": [{"name": publisher, "url": link}],
        })

    return output


def same_story(first: dict[str, Any], second: dict[str, Any]) -> bool:
    ratio = similarity(first["title"], second["title"])
    if ratio >= 0.62:
        return True
    first_words = significant_words(first["title"])
    second_words = significant_words(second["title"])
    return len(first_words & second_words) >= 3


def merge_stories(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items.sort(key=lambda item: (item.get("source_priority", 40), item["published_at"]), reverse=True)

    groups: list[list[dict[str, Any]]] = []
    for item in items:
        matching: list[dict[str, Any]] | None = None
        for group in groups:
            if same_story(item, group[0]):
                matching = group
                break
        if matching is None:
            groups.append([item])
        else:
            matching.append(item)

    merged: list[dict[str, Any]] = []
    for group in groups:
        group.sort(key=lambda item: item.get("source_priority", 40), reverse=True)
        lead = dict(group[0])

        all_sources: list[dict[str, str]] = []
        for item in group:
            all_sources.extend(item.get("sources", []))
        ranked_sources = rank_sources(all_sources)
        if not ranked_sources:
            continue

        lead["sources"] = ranked_sources
        lead["main_source"] = ranked_sources[0]
        lead["confirmed_by"] = ranked_sources[1:5]
        lead["status"] = source_status(ranked_sources[0]["name"], len(ranked_sources))
        lead["rank_score"] = max(item.get("source_priority", 40) for item in group) + min(30, (len(ranked_sources) - 1) * 10)
        lead["id"] = re.sub(r"[^a-z0-9]+", "-", normalize(lead["title"])).strip("-")[:90]

        summary_candidates = [
            clean_text(item.get("summary", ""))
            for item in group
            if clean_text(item.get("summary", ""))
        ]
        if summary_candidates:
            summary_candidates.sort(
                key=lambda text: (similarity(lead["title"], text) < 0.80, len(text)),
                reverse=True,
            )
            lead["summary"] = summary_candidates[0][:850]
        elif not lead.get("summary"):
            lead["summary"] = ""

        lead.pop("source_priority", None)
        merged.append(lead)

    merged.sort(key=lambda item: (item["published_at"], item["rank_score"]), reverse=True)
    return merged


def build_fallback(source_name: str) -> str:
    name = (source_name or "").strip()
    if not name:
        return "Läs hela artikeln hos originalkällan."
    return f"Läs hela artikeln hos {name} (originalspråk, se länk)."


def enrich_summary(item: dict[str, Any]) -> None:
    current_summary = clean_text(item.get("summary", ""))
    needs_intro = len(current_summary) < 60

    source = item.get("main_source") or (item.get("sources") or [{}])[0]
    url = source.get("url", "")
    if not url:
        if not current_summary:
            item["summary"] = build_fallback(source.get("name", ""))
        return

    resolved = resolve_article_url(url)
    if resolved and resolved != url:
        source["url"] = resolved
        for other in item.get("sources", []):
            if other.get("url") == url:
                other["url"] = resolved
        url = resolved

    if needs_intro or not item.get("image"):
        intro, og_image = extract_article_metadata(url, item.get("title", ""))
        if intro and needs_intro:
            item["summary"] = intro
        if og_image:
            item["image"] = og_image

    if not clean_text(item.get("summary", "")):
        item["summary"] = build_fallback(source.get("name", ""))


def enrich_selected(items: list[dict[str, Any]], workers: int = 8) -> None:
    if not items:
        return
    with ThreadPoolExecutor(max_workers=workers) as executor:
        list(executor.map(enrich_summary, items))


def main() -> int:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    cutoff = NOW - dt.timedelta(days=int(config.get("max_age_days", 10)))

    collected: list[dict[str, Any]] = []
    for source in config["feeds"]:
        if source["type"] == "rss":
            url = source["url"]
        else:
            url = google_news_url(
                source["query"],
                source.get("hl", "en-US"),
                source.get("gl", "US"),
                source.get("ceid", "US:en"),
                int(config.get("max_age_days", 10)),
            )
        try:
            collected.extend(parse_feed(fetch(url), source, cutoff))
        except Exception as exc:
            print(f"WARN {source['name']}: {exc}")

    if not collected:
        print("Inga färska nyheter hämtades; behåller befintlig news.json.")
        return 0

    merged = merge_stories(collected)

    selected: list[dict[str, Any]] = []
    publisher_counts: dict[str, int] = {}
    max_items = int(config.get("max_items", 40))

    for item in merged:
        source_name = item["main_source"]["name"]
        limit = 12 if source_name in SOURCE_RANK else 5
        if publisher_counts.get(source_name, 0) >= limit:
            continue
        publisher_counts[source_name] = publisher_counts.get(source_name, 0) + 1

        item = dict(item)
        item.pop("rank_score", None)
        selected.append(item)
        if len(selected) >= max_items:
            break

    if not selected:
        print("Inga godkända nyheter kvar efter filtrering; behåller befintlig news.json.")
        return 0

    enrich_selected(selected)

    payload = {"updated_at": NOW.isoformat(), "items": selected}
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    unique_sources = len({s["name"] for i in selected for s in i["sources"]})
    print(f"Skrev {len(selected)} nyheter från {unique_sources} källor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
