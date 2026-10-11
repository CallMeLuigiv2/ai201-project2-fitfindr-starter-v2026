"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

    python agent.py          runs both example paths below
"""

import re

import config  # noqa: F401 — loads .env and sets the console to UTF-8
import trace
from tools import (
    FILLER_WORDS,
    create_fit_card,
    format_price,
    search_listings,
    size_matches,
    suggest_outfit,
)
from generate import ModelUnavailable  # noqa: F401 — handled in unit 4
from mcp_client import call_tool
from utils.data_loader import load_listings


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one chosen — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }


# ── parsing the query ─────────────────────────────────────────────────────────

_PRICE_WORDS = r"(?:under|below|less than|up to|max)"
# "under $30", "$30", "under 30"
_PRICE = re.compile(
    rf"(?:{_PRICE_WORDS}\s*)?\$\s*(\d+(?:\.\d+)?)|{_PRICE_WORDS}\s+(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
# "size M", "size 8.5", "size W30"
_SIZE = re.compile(r"\bsize\s+([a-z0-9./]+)", re.IGNORECASE)


def _parse_query(query: str) -> dict:
    """
    Pull a price ceiling and a size out of the query with regex. The words
    left over, minus filler, are the description.

        "looking for a vintage graphic tee under $30, size M"
        → {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}
    """
    max_price = None
    price = _PRICE.search(query)
    if price:
        max_price = float(price.group(1) or price.group(2))
        query = query[: price.start()] + " " + query[price.end():]

    size = None
    size_found = _SIZE.search(query)
    if size_found:
        size = size_found.group(1).rstrip("./").upper()
        query = query[: size_found.start()] + " " + query[size_found.end():]

    words = [
        word for word in re.findall(r"[a-z0-9'-]+", query.lower())
        if word.replace("'", "") not in FILLER_WORDS
    ]
    return {"description": " ".join(words), "size": size, "max_price": max_price}


# ── the stop message ──────────────────────────────────────────────────────────

def _why_empty(parsed: dict) -> str:
    """
    The message for a search that found nothing. Checks each filter to say
    which ones ruled everything out, so the user knows what to change.
    """
    description = parsed["description"]
    size = parsed["size"]
    max_price = parsed["max_price"]

    asked = f'"{description}"' if description else "your search"
    if size:
        asked += f" in size {size}"
    if max_price is not None:
        asked += f" under {format_price(max_price)}"

    listings = load_listings()
    keyword_matches = search_listings(description)
    problems = []

    if not keyword_matches:
        # Nothing matches the words, so size and price can only be checked
        # against the data as a whole.
        if description:
            problems.append(
                f'Words: nothing matches "{description}". Try an item type '
                '("jacket", "jeans") or a style ("vintage", "y2k").'
            )
        else:
            problems.append('Words: say what you\'re looking for, like "denim jacket".')

        if size and not any(size_matches(size, x["size"]) for x in listings):
            problems.append(f"Size: no listing comes in size {size}. Try another size, or leave it out.")

        if max_price is not None and not any(x["price"] <= max_price for x in listings):
            cheapest = min(x["price"] for x in listings)
            problems.append(
                f"Price: nothing costs {format_price(max_price)} or less. "
                f"The cheapest listing is {format_price(cheapest)}."
            )
    else:
        # The words match, so the size, the price, or the two together are
        # what emptied it. Try each one with the other left off.
        size_blocks = size and not search_listings(description, size=size)
        price_blocks = max_price is not None and not search_listings(description, max_price=max_price)

        if size_blocks:
            problems.append(f'Size: nothing matching "{description}" comes in size {size}. Try another size, or leave it out.')
        if price_blocks:
            in_size = search_listings(description, size=size) or keyword_matches
            cheapest = min(x["price"] for x in in_size)
            problems.append(
                f'Price: the cheapest match for "{description}" is {format_price(cheapest)}. '
                "Raise your max price to at least that."
            )
        if not size_blocks and not price_blocks:
            problems.append(
                f"Size and price: there are matches in size {size} and matches under "
                f"{format_price(max_price)}, but none that are both. Loosen one of them."
            )

    return f"No listings matched {asked}. What to change:\n    - " + "\n    - ".join(problems)


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields are still None.

    Each time round the loop runs one tool, then picks the next one from what
    that tool returned. An empty search is the branch: the loop stops with a
    message instead of calling suggest_outfit with nothing.
    """
    session = new_session(query, wardrobe)
    session["parsed"] = _parse_query(query)

    next_step = "search_listings"
    count = 0
    while next_step is not None:
        count += 1
        trace.check_iterations(count)

        if next_step == "search_listings":
            parsed = session["parsed"]
            # Through the MCP server, not a direct call. Same function on the
            # other side, so the list that comes back is the same.
            session["search_results"] = call_tool("search_listings", {
                "description": parsed["description"],
                "size": parsed["size"],
                "max_price": parsed["max_price"],
            })
            if not session["search_results"]:
                # THE BRANCH: nothing to style, so stop before suggest_outfit.
                session["error"] = _why_empty(parsed)
                next_step = None
            else:
                session["selected_item"] = session["search_results"][0]
                next_step = "suggest_outfit"

        elif next_step == "suggest_outfit":
            session["outfit_suggestion"] = suggest_outfit(
                session["selected_item"], session["wardrobe"]
            )
            next_step = "create_fit_card"

        elif next_step == "create_fit_card":
            session["fit_card"] = create_fit_card(
                session["outfit_suggestion"], session["selected_item"]
            )
            next_step = None

    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
