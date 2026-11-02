"""Deterministic extraction from fetched content. Fetched content is untrusted data:
it is parsed, never executed, and never forwarded to a model unsanitised."""
import html
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin

INJECTION = re.compile(
    r"ignore (all |any )?(previous|prior|above) (instructions|prompts)|disregard (the )?(system|previous)|"
    r"you are now|system prompt|reveal your|act as (an? )?(ai|assistant)", re.I)
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize(text: str, limit: int = 300) -> str:
    """Single line, no control characters, capped. Safe to put in a log or a prompt field."""
    return _CTRL.sub("", " ".join(text.split()))[:limit]


def untrusted(text: str, limit: int = 2000) -> str:
    """Wrap external text so a model treats it as data, not instructions."""
    body = sanitize(text, limit).replace("<", "(").replace(">", ")")
    return f"<untrusted_data>{body}</untrusted_data>"


def looks_like_injection(text: str) -> bool:
    return bool(INJECTION.search(text))


@dataclass
class ParsedPage:
    title: str = ""
    meta: dict[str, str] = field(default_factory=dict)
    jsonld: list[str] = field(default_factory=list)  # raw JSON strings
    links: list[str] = field(default_factory=list)
    stylesheets: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    text: str = ""


class _Parser(HTMLParser):
    def __init__(self, base: str):
        super().__init__(convert_charrefs=True)
        self.base, self.page = base, ParsedPage()
        self._in_title = self._skip = False
        self._ld = False
        self._buf: list[str] = []
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = a.get("property") or a.get("name")
            if key and "content" in a:
                self.page.meta.setdefault(key.lower(), a["content"])
        elif tag == "a" and a.get("href", "").strip() and not a["href"].startswith(("javascript:", "#", "mailto:", "tel:")):
            self.page.links.append(urljoin(self.base, a["href"].strip()))
        elif tag == "link" and "stylesheet" in a.get("rel", "").lower() and a.get("href"):
            self.page.stylesheets.append(urljoin(self.base, a["href"]))
        elif tag == "img" and a.get("src"):
            self.page.images.append(urljoin(self.base, a["src"]))
        elif tag == "script":
            self._ld = "ld+json" in a.get("type", "").lower()
            self._skip = True
        elif tag == "style":
            self._skip = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script":
            if self._ld and self._buf:
                self.page.jsonld.append("".join(self._buf))
            self._ld, self._buf, self._skip = False, [], False
        elif tag == "style":
            self._skip = False

    def handle_data(self, data):
        if self._in_title:
            self.page.title += data
        if self._ld:
            self._buf.append(data)
        elif not self._skip and len(self._text) < 4000:
            self._text.append(data)


def parse_html(raw: str, base_url: str) -> ParsedPage:
    p = _Parser(base_url)
    p.feed(raw)
    p.close()  # flush text held back at end of input (Python 3.14 buffers an unterminated <title> as RCDATA)
    p.page.title = " ".join(p.page.title.split())
    p.page.text = " ".join(" ".join(p._text).split())[:20000]
    return p.page


def searchable_text(raw: str) -> str:
    """Raw HTML plus decoded JSON-LD, so evidence excerpts can be located reliably."""
    page = parse_html(raw, "https://invalid.example/")
    parts = [raw, html.unescape(raw)]
    for block in page.jsonld:
        try:
            parts.append(json.dumps(json.loads(block), ensure_ascii=False))
        except ValueError:
            pass
    return "\n".join(parts)


# --- JSON-LD products -----------------------------------------------------
def _walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def _as_list(v):
    return v if isinstance(v, list) else ([] if v is None else [v])


def jsonld_products(blocks: list[str]) -> list[dict]:
    out = []
    for b in blocks:
        try:
            doc = json.loads(b)
        except ValueError:
            continue
        for n in _walk(doc):
            if "Product" not in _as_list(n.get("@type")):
                continue
            offers = []
            for o in _as_list(n.get("offers")):
                for oo in (_as_list(o.get("offers")) or [o]):
                    if isinstance(oo, dict) and oo.get("sku") is not None:
                        offers.append({k: oo.get(k) for k in
                                       ("sku", "name", "price", "priceCurrency", "gtin13", "availability", "url")})
            rating = n.get("aggregateRating") if isinstance(n.get("aggregateRating"), dict) else {}
            out.append({
                "name": n.get("name", ""), "sku": str(n.get("sku", "")), "description": n.get("description", ""),
                "brand": (n["brand"].get("name", "") if isinstance(n.get("brand"), dict) else str(n.get("brand") or "")),
                "brand": (n["brand"].get("name", "") if isinstance(n.get("brand"), dict) else str(n.get("brand") or "")),
                "images": [i for i in _as_list(n.get("image")) if isinstance(i, str)], "offers": offers,
                "rating": {"ratingValue": rating.get("ratingValue"), "reviewCount": rating.get("reviewCount")}
                if rating else {},
                "certifications": [c.get("name", "") for c in _as_list(n.get("hasCertification")) if isinstance(c, dict)],
            })
    return out


_SIZE = re.compile(r"(\d+(?:[.,]\d+)?\s?(?:kg|g|ml|l|kaps\.?|caps))\b", re.I)


def split_variant(offer_name: str) -> tuple[str, str]:
    """('1000 g', 'zelena jabuka') from '... 1000 g - zelena jabuka'. Empty strings if absent."""
    m = _SIZE.search(offer_name)
    if not m:
        return "", ""
    rest = offer_name[m.end():].strip(" -–.")
    return m.group(1), rest


def item_list_urls(blocks: list[str]) -> list[str]:
    """Product URLs from schema.org ItemList entries (category listing pages)."""
    out = []
    for b in blocks:
        try:
            doc = json.loads(b)
        except ValueError:
            continue
        for n in _walk(doc):
            if "ItemList" in _as_list(n.get("@type")):
                for el in _as_list(n.get("itemListElement")):
                    if isinstance(el, dict) and isinstance(el.get("url"), str):
                        out.append(el["url"])
    return list(dict.fromkeys(out))


# --- CSS ------------------------------------------------------------------
_GENERIC = {"sans-serif", "serif", "monospace", "inherit", "initial", "unset", "cursive", "system-ui",
            "ui-sans-serif", "ui-serif", "ui-monospace", "emoji", "math", "fantasy", "-apple-system"}


def css_stats(css: str, top: int = 8) -> dict:
    fonts = Counter()
    for decl in re.findall(r"font-family\s*:\s*([^;}{]+)", css, re.I):
        for f in decl.split(","):
            f = f.strip().strip("'\"").strip()
            if f and not f.startswith("var(") and f.lower() not in _GENERIC:
                fonts[f] += 1
    colors = Counter()
    for c in re.findall(r"#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", css):
        c = c.lower()
        if len(c) == 3:
            c = "".join(ch * 2 for ch in c)
        colors["#" + c[:6]] += 1
    return {"fonts": fonts.most_common(top), "colors": colors.most_common(top * 3)}


def is_neutral(hex_color: str) -> bool:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return max(r, g, b) - min(r, g, b) < 24
