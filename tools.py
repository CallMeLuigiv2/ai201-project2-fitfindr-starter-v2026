"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

The spec for each one is in the README, under **Tool Inventory**.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# Words that say nothing about the item. "looking for a vintage tee" should
# search for "vintage tee", not for listings that contain "for".
FILLER_WORDS = {
    "a", "an", "and", "any", "find", "for", "get", "i", "im", "in", "is",
    "looking", "me", "my", "need", "of", "or", "please", "show", "some",
    "something", "that", "the", "to", "want", "with",
}

# A keyword found in the title is a stronger signal than one found in a tag:
# "jacket" only ever appears in titles, while a tag like "vintage" is on a
# quarter of the listings.
TITLE_WEIGHT = 2
TAG_WEIGHT = 1
CATEGORY_WEIGHT = 1


def format_price(price: float) -> str:
    """18.0 → "$18", 18.5 → "$18.50"."""
    return f"${price:.0f}" if price == int(price) else f"${price:.2f}"


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def _keywords(text: str) -> set[str]:
    """
    Lowercase words, minus filler, with a trailing "s" dropped so "tees"
    matches "tee" and "jeans" matches "jean". Short words like "90s" keep
    their "s".
    """
    words = set()
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        if len(word) < 2 or word in FILLER_WORDS:
            continue
        if len(word) > 3 and word.endswith("s"):
            word = word[:-1]
        words.add(word)
    return words


def _size_pieces(size: str) -> set[str]:
    """ "S/M" → {"s", "m"}, "US 8.5" → {"us", "8.5"}, "XL (oversized)" → {"xl", "oversized"} """
    return {piece for piece in re.split(r"[\s/()]+", size.lower()) if piece}


def size_matches(wanted: str, listing_size: str) -> bool:
    """
    True when the listing has every piece of the size asked for, or is
    One Size. Whole pieces only, so "S" matches "S/M" but not "US 9", and
    "L" matches "L/XL" but not "XL".
    """
    if listing_size.lower().startswith("one size"):
        return True
    return _size_pieces(wanted) <= _size_pieces(listing_size)


def _score(listing: dict, wanted: set[str]) -> int:
    title = _keywords(listing["title"])
    tags = _keywords(" ".join(listing["style_tags"]))
    category = _keywords(listing["category"])

    score = 0
    for word in wanted:
        if word in title:
            score += TITLE_WEIGHT
        if word in tags:
            score += TAG_WEIGHT
        if word in category:
            score += CATEGORY_WEIGHT
    return score


def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings for items matching a description, and optionally a
    size and a price ceiling.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size to filter by, or None to skip size filtering.
                     See size_matches() for what counts as a match.
        max_price:   maximum price in dollars, inclusive, or None to skip.

    Returns:
        Up to config.SEARCH_RESULT_LIMIT listing dicts, highest keyword score
        first, cheapest first on a tie. An empty list when nothing matches —
        never None, never an exception.

    Test it from a terminal:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    wanted = _keywords(description)

    scored = []
    for listing in load_listings():
        if max_price is not None and listing["price"] > max_price:
            continue
        if size and not size_matches(size, listing["size"]):
            continue
        score = _score(listing, wanted)
        if score > 0:
            scored.append((score, listing))

    scored.sort(key=lambda pair: (-pair[0], pair[1]["price"]))
    return [listing for _, listing in scored[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def _describe_listing(item: dict) -> str:
    """The item as prompt text. Fields that are empty are left out, so the
    model never sees "brand: None"."""
    lines = [
        f"Item: {item['title']}",
        f"Category: {item['category']}",
        f"Colors: {', '.join(item['colors'])}",
        f"Style: {', '.join(item['style_tags'])}",
        f"Size: {item['size']}",
        f"Condition: {item['condition']}",
        f"Price: {format_price(item['price'])} on {item['platform']}",
    ]
    if item.get("brand"):
        lines.append(f"Brand: {item['brand']}")
    return "\n".join(lines)


def _describe_wardrobe_item(piece: dict) -> str:
    line = f"- {piece['name']} ({piece['category']}; {', '.join(piece['colors'])})"
    if piece.get("notes"):
        line += f", note: {piece['notes']}"
    return line


_STYLIST = (
    "You are a friendly stylist for thrift shoppers. Give concrete, wearable "
    "outfit ideas in plain text, no markdown, under 120 words."
)


def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  It may be empty.

    Returns:
        A non-empty string. With wardrobe items, the outfits name pieces the
        user owns. With an empty wardrobe, general styling ideas instead.

    Test it from a terminal:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    pieces = (wardrobe or {}).get("items") or []

    if pieces:
        owned = "\n".join(_describe_wardrobe_item(p) for p in pieces)
        prompt = (
            f"{_describe_listing(new_item)}\n\n"
            f"The user already owns:\n{owned}\n\n"
            "Suggest one or two outfits built around the item. Each outfit must "
            "name at least two pieces from the list above, using their names "
            "as written."
        )
    else:
        prompt = (
            f"{_describe_listing(new_item)}\n\n"
            "The user hasn't saved any clothes yet. Suggest one or two outfits "
            "built around the item, using common pieces (for example "
            "'straight-leg jeans' or 'white sneakers')."
        )

    outfit = generate(prompt, system=_STYLIST)
    return outfit or f"Style the {new_item['title']} with simple basics in matching colors."


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

_CAPTION_WRITER = (
    "You write short social media captions about thrift finds, in the first "
    "person, like a real post. Plain text, no hashtags, no markdown."
)


def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption that mentions the item, its price and
        its platform once each. If `outfit` is empty or whitespace, a message
        saying so, and the model is not called.

    Test it from a terminal:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return "Can't write a fit card: there's no outfit suggestion for this item yet."

    price = format_price(new_item["price"])
    prompt = (
        f"{_describe_listing(new_item)}\n\n"
        f"How I'm wearing it:\n{outfit}\n\n"
        "Write a 2 to 4 sentence caption, under 60 words, about this find. "
        f"Mention the item, the price written exactly as {price}, and "
        f"{new_item['platform']}, once each. Be specific about the vibe. "
        "Only mention a brand if one is listed above."
    )
    return generate(prompt, system=_CAPTION_WRITER)
