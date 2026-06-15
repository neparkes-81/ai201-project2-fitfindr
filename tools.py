"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# Groq chat model used by the LLM-backed tools (suggest_outfit, create_fit_card).
MODEL = "llama-3.3-70b-versatile"


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── search helpers ──────────────────────────────────────────────────────────

# Filler words that carry no signal for keyword relevance scoring.
_STOPWORDS = {
    "a", "an", "the", "for", "under", "in", "on", "with", "size", "sized",
    "looking", "look", "want", "wanted", "need", "needs", "im", "i", "my",
    "me", "and", "or", "of", "to", "that", "this", "some", "please", "find",
    "something", "any", "is", "are", "be", "but", "out", "there", "got",
}


def _tokenize(text: str) -> list[str]:
    """Lowercase `text` and split it into alphanumeric word tokens."""
    if not text:
        return []
    return re.findall(r"[a-z0-9]+", text.lower())


def _size_matches(requested: str, listing_size: str) -> bool:
    """
    Case-insensitive size match.

    A listing matches when every token of the requested size appears among the
    listing's size tokens (split on slashes and whitespace). This lets "M" match
    "S/M" or "M/L", "8" match "US 8", and "W30" match "W30 L30", while keeping
    sizes like "XXS" from matching anything in the catalog.
    """
    req_tokens = [t for t in re.split(r"[\s/]+", requested.strip().lower()) if t]
    if not req_tokens:
        return True
    listing_tokens = {t for t in re.split(r"[\s/]+", (listing_size or "").lower()) if t}
    return all(t in listing_tokens for t in req_tokens)


def _score_listing(keywords: list[str], listing: dict) -> int:
    """
    Score a listing by weighted keyword overlap with the search description.

    Fields are weighted by how strongly they signal relevance: a hit in the
    title or style tags counts more than a passing mention in the description.
    """
    title = (listing.get("title") or "").lower()
    tags = " ".join(listing.get("style_tags") or []).lower()
    category = (listing.get("category") or "").lower()
    colors = " ".join(listing.get("colors") or []).lower()
    brand = (listing.get("brand") or "").lower()
    description = (listing.get("description") or "").lower()

    score = 0
    for kw in keywords:
        if kw in title:
            score += 3
        if kw in tags:
            score += 3
        if kw in category:
            score += 2
        if kw in brand:
            score += 2
        if kw in colors:
            score += 1
        if kw in description:
            score += 1
    return score


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()

    # Keywords that drive relevance scoring (filler words removed).
    keywords = [t for t in _tokenize(description) if t not in _STOPWORDS]

    scored: list[tuple[int, dict]] = []
    for listing in listings:
        # Apply hard filters first — these are constraints, not preferences.
        if max_price is not None and listing.get("price", float("inf")) > max_price:
            continue
        if size is not None and not _size_matches(size, listing.get("size", "")):
            continue

        # If the caller gave no usable keywords, every filtered listing is equally
        # relevant; otherwise require at least one keyword hit.
        if not keywords:
            scored.append((0, listing))
            continue

        score = _score_listing(keywords, listing)
        if score > 0:
            scored.append((score, listing))

    # Sort by relevance, highest first. Python's sort is stable, so listings with
    # equal scores keep their original catalog order.
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [listing for _, listing in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    item_desc = _describe_item(new_item)
    items = (wardrobe or {}).get("items") or []

    if not items:
        # No wardrobe to pull from — give general styling direction for the piece.
        prompt = (
            f"A shopper is considering buying this secondhand item:\n{item_desc}\n\n"
            "They haven't told us what's in their closet yet. In 3-5 sentences, give "
            "general styling advice: what kinds of pieces (tops/bottoms/shoes/layers) "
            "pair well with it, what occasions or vibe it suits, and one specific "
            "styling tip. Be warm and concrete, not generic."
        )
    else:
        wardrobe_text = _format_wardrobe(items)
        prompt = (
            f"A shopper is considering buying this secondhand item:\n{item_desc}\n\n"
            f"Here is what's already in their wardrobe:\n{wardrobe_text}\n\n"
            "Suggest 1-2 complete outfits that combine the new item with specific, "
            "named pieces from their wardrobe (refer to the wardrobe items by name). "
            "For each outfit, name the pieces and add a short note on the overall vibe. "
            "Keep it to a few sentences per outfit and only use pieces listed above."
        )

    fallback = (
        "Couldn't reach the styling model right now, but this piece is versatile — "
        "try pairing it with simple basics in neutral tones and let it be the "
        "statement of the outfit."
    )
    return _chat(
        system="You are FitFindr, a friendly, practical secondhand-fashion stylist.",
        user=prompt,
        temperature=0.7,
        fallback=fallback,
    )


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # Guard: without an outfit there is nothing to caption.
    if not outfit or not outfit.strip():
        return (
            "Can't write a fit card yet — no outfit suggestion was provided. "
            "Generate an outfit with suggest_outfit() first."
        )

    item = new_item or {}
    title = item.get("title") or "this thrifted find"
    price = item.get("price")
    platform = item.get("platform") or "a resale app"
    price_text = f"${price:g}" if isinstance(price, (int, float)) else "a steal"

    prompt = (
        f"Write a short, shareable Instagram/TikTok caption (2-4 sentences) for an "
        f"outfit built around a thrifted find.\n\n"
        f"Item: {title}\n"
        f"Price: {price_text}\n"
        f"Platform: {platform}\n"
        f"Outfit: {outfit}\n\n"
        "Make it sound like a real OOTD post — casual, authentic, a little playful. "
        f"Work in the item name, the price ({price_text}), and the platform "
        f"({platform}) naturally, each mentioned once. Capture the outfit's vibe in "
        "specific terms. Emojis are welcome but optional. Return only the caption text."
    )

    fallback = (
        f"just thrifted {title} off {platform} for {price_text} and i'm obsessed 🛍️ "
        "styled it up and it's officially in the rotation. full look soon!"
    )
    return _chat(
        system="You write punchy, authentic social-media fashion captions.",
        user=prompt,
        temperature=0.9,
        fallback=fallback,
    )


# ── LLM + formatting helpers ──────────────────────────────────────────────────

def _describe_item(item: dict) -> str:
    """Render a listing dict into a compact, readable block for an LLM prompt."""
    item = item or {}
    parts = [
        f"Title: {item.get('title', 'Unknown item')}",
        f"Category: {item.get('category', 'unknown')}",
        f"Description: {item.get('description', '')}",
        f"Style tags: {', '.join(item.get('style_tags') or []) or 'n/a'}",
        f"Colors: {', '.join(item.get('colors') or []) or 'n/a'}",
        f"Brand: {item.get('brand') or 'unbranded'}",
        f"Size: {item.get('size', 'n/a')}",
        f"Condition: {item.get('condition', 'n/a')}",
    ]
    return "\n".join(parts)


def _format_wardrobe(items: list[dict]) -> str:
    """Render wardrobe items into a numbered list for an LLM prompt."""
    lines = []
    for i, it in enumerate(items, start=1):
        name = it.get("name", "Unnamed item")
        category = it.get("category", "")
        colors = ", ".join(it.get("colors") or [])
        tags = ", ".join(it.get("style_tags") or [])
        notes = it.get("notes")
        detail = f"{name} ({category}"
        if colors:
            detail += f"; {colors}"
        if tags:
            detail += f"; {tags}"
        detail += ")"
        if notes:
            detail += f" — {notes}"
        lines.append(f"{i}. {detail}")
    return "\n".join(lines)


def _chat(system: str, user: str, temperature: float, fallback: str) -> str:
    """
    Send a single-turn chat request to Groq and return the response text.

    Any failure (missing API key, network/API error, empty response) is caught
    and the provided `fallback` string is returned, so callers always get a
    usable non-empty string and never raise into the agent loop.
    """
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        content = (response.choices[0].message.content or "").strip()
        return content or fallback
    except Exception:
        return fallback
