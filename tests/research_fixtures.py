"""Recorded/synthetic fixtures for research tests.

These are HAND-AUTHORED test fixtures shaped like the real gymbeam.hr pages and Apify output
(JSON-LD Product/ItemList, meta tags, CSS). They are not recordings of live traffic and are
never reported as real collected data.
"""
import json
from types import SimpleNamespace

from studio.contracts import BriefInput, ProviderKind
from studio.providers.live import ScriptedResearchPolicy, UnavailableProvider
from studio.tools.instagram import APIFY_ACTOR
from studio.tools.toolset import ResearchToolset
from studio.tools.transport import RecordedTransport
from studio.tools.web import HttpClient

SITE = "https://gymbeam.hr"
FIXED_NOW = "2026-01-01T00:00:00+00:00"
def jpeg(tag: str) -> bytes:
    """Distinct synthetic JPEG-magic bytes per tag (not a real picture)."""
    return b"\xff\xd8\xff\xe0" + f"synthetic-jpeg-fixture-{tag}-".encode() * 20
APIFY_URL = f"https://api.apify.com/v2/acts/{APIFY_ACTOR}/run-sync-get-dataset-items?maxTotalChargeUsd=0.1"


def brief(**kw) -> BriefInput:
    base = dict(brand_name="GymBeam", product_name="Creatine", campaign_goal="research only", audience="tbd",
                website_url=SITE, instagram_handle="gymbeamhr", seed_urls=[f"{SITE}/kreatin-monohidrat"],
                focus_keywords=["kreatin"], language="hr")
    return BriefInput(**{**base, **kw})


def offer(sku, name, price, gtin):
    return {"@type": "Offer", "sku": sku, "name": name, "price": price, "priceCurrency": "EUR",
            "gtin13": gtin, "availability": "https://schema.org/InStock", "url": f"{SITE}/p.html#{sku}"}


def product_page(sku, name, offers, images, description="Opis proizvoda."):
    ld = {"@context": "https://schema.org", "@graph": [{
        "@type": "Product", "name": name, "sku": sku, "description": description, "image": images,
        "brand": {"@type": "Brand", "name": "GymBeam"},
        "aggregateRating": {"@type": "AggregateRating", "ratingValue": 4.8, "reviewCount": 8},
        "offers": {"@type": "AggregateOffer", "offers": offers}}]}
    return (f'<html><head><title>{name}</title><script type="application/ld+json">{json.dumps(ld)}</script>'
            f"</head><body>product</body></html>")


A_URL, B_URL = f"{SITE}/kreatin-a.html", f"{SITE}/kreatin-b.html"
A_OFFERS = [offer("A1", "100% Kreatin Monohidrat - GymBeam 1000 g - zelena jabuka", 29.95, "8580000000011"),
            offer("A2", "100% Kreatin Monohidrat - GymBeam 1000 g - bez okusa", 28.95, "8580000000028"),
            offer("A3", "100% Kreatin Monohidrat - GymBeam 500 g - bez okusa", 15.95, "8580000000035")]
B_OFFERS = [offer("B1", "Kreatin Monohidrat – GymBeam 120 kaps.", 8.95, "8580000000042")]
IMG_A1, IMG_A2, IMG_B1 = (f"{SITE}/media/{n}.jpg" for n in ("a_old", "a_new", "b_caps"))


def category_page():
    ld = {"@graph": [{"@type": "ItemList", "itemListElement": [
        {"@type": "ListItem", "url": A_URL}, {"@type": "ListItem", "url": B_URL}]}]}
    return (f'<html><head><title>Kreatin</title><script type="application/ld+json">{json.dumps(ld)}</script>'
            f'</head><body><a href="/other">x</a></body></html>')


HOME = ('<html><head><title>GymBeam HR</title><meta property="og:site_name" content="GYMBEAM.HR">'
        '<meta property="og:description" content="Test opis trgovine">'
        '<meta name="theme-color" content="#ff8c32"><link rel="stylesheet" href="/s.css"></head>'
        '<body><a href="/kreatin-monohidrat">kreatin</a></body></html>')
CSS = "body{font-family:Inter,Arial,sans-serif;color:#ff4100}.a{background:#ff4100}.b{color:#8bc34a;font-family:'Inter'}"
ROBOTS = "User-agent: *\nDisallow: /checkout/\n"


def apify_items():
    def item(code, owner, likes, caption, typ="Video"):
        return {"shortCode": code, "url": f"https://www.instagram.com/p/{code}/", "type": typ,
                "timestamp": "2026-10-20T16:00:00.000Z", "caption": caption, "likesCount": likes,
                "commentsCount": 0, "hashtags": ["gymbeamhr"], "ownerUsername": owner}
    return [item("AAA111", "gymbeamhr", 22, "Prvi post \U0001F525 Istražite na linku u opisu profila!"),
            item("BBB222", "gymbeamhr", -1, "Drugi post, lajkovi skriveni", "Sidecar"),
            item("CCC333", "creator_x", 5, "Collab by someone else")]


def site(t: RecordedTransport | None = None, *, with_products=True, apify=True) -> RecordedTransport:
    t = t or RecordedTransport()
    t.add(f"{SITE}/robots.txt", body=ROBOTS, content_type="text/plain")
    t.add(SITE, body=HOME)
    t.add(f"{SITE}/s.css", body=CSS, content_type="text/css")
    t.add(f"{SITE}/kreatin-monohidrat", body=category_page())
    if with_products:
        t.add(A_URL, body=product_page("A", "100% Kreatin Monohidrat - GymBeam", A_OFFERS, [IMG_A1, IMG_A2]))
        t.add(B_URL, body=product_page("B", "Kreatin Monohidrat – GymBeam", B_OFFERS, [IMG_B1]))
        for u in (IMG_A1, IMG_A2, IMG_B1):
            t.add(u, body=jpeg(u.rsplit("/", 1)[-1]), content_type="image/jpeg")
    if apify:
        t.add(APIFY_URL, method="POST", body=json.dumps(apify_items()), content_type="application/json")
    return t


def providers(transport, cfg, *, llm=None, ig=None, clock=lambda: FIXED_NOW):
    http = HttpClient(transport, cfg, sleep=lambda s: None)
    holder = SimpleNamespace(toolset=None, http=http)

    def factory(run_dir):
        holder.toolset = ResearchToolset(run_dir, http, cfg, origin="fixture", instagram=ig, clock=clock)
        return holder.toolset

    no = lambda k: UnavailableProvider(k, "not part of research")  # noqa: E731
    holder.providers = SimpleNamespace(
        llm=llm or ScriptedResearchPolicy(), vision=no(ProviderKind.VISION), image=no(ProviderKind.IMAGE),
        video=no(ProviderKind.VIDEO), research=factory)
    return holder
