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

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


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
    """
    listings = load_listings()

    # Filter by price and size
    candidates = []
    for item in listings:
        if max_price is not None and item["price"] > max_price:
            continue
        if size is not None and size.upper() not in item["size"].upper():
            continue
        candidates.append(item)

    # Build a searchable text blob for each candidate and score by keyword overlap
    keywords = [w.lower() for w in description.split() if w]

    def score(item):
        searchable = " ".join([
            item["title"],
            item["description"],
            item["category"],
            " ".join(item.get("style_tags", [])),
            " ".join(item.get("colors", [])),
            item.get("brand") or "",
        ]).lower()
        return sum(1 for kw in keywords if kw in searchable)

    scored = [(score(item), item) for item in candidates]
    scored = [(s, item) for s, item in scored if s > 0]
    scored.sort(key=lambda x: x[0], reverse=True)

    return [item for _, item in scored[:3]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions, or None if the wardrobe
        items are incompatible with the new item.
        If the wardrobe is empty, returns general styling advice instead.
    """
    items = wardrobe.get("items", [])
    client = _get_groq_client()

    # Describe the new item for the LLM
    new_item_text = (
        f"{new_item['title']} — {new_item['description']} "
        f"(category: {new_item['category']}, "
        f"style tags: {', '.join(new_item.get('style_tags', []))}, "
        f"colors: {', '.join(new_item.get('colors', []))})"
    )

    if not items:
        prompt = (
            "You are a personal stylist helping someone style a thrifted find. "
            "The user's wardrobe is empty, so give general styling advice for the item.\n\n"
            f"New item:\n{new_item_text}\n\n"
            "Describe what kinds of clothing pieces pair well with this item, "
            "what vibe or aesthetic it suits, and what occasions it works for. "
            "Keep your advice to 2–3 sentences."
        )
    else:
        # Format wardrobe items into a readable list
        wardrobe_lines = []
        for item in items:
            colors = ", ".join(item.get("colors", []))
            tags = ", ".join(item.get("style_tags", []))
            line = f"- {item['name']} (colors: {colors}, style: {tags})"
            if item.get("notes"):
                line += f" — {item['notes']}"
            wardrobe_lines.append(line)
        wardrobe_text = "\n".join(wardrobe_lines)

        prompt = (
            "You are a personal stylist helping someone style a thrifted find.\n\n"
            f"New item:\n{new_item_text}\n\n"
            f"User's wardrobe:\n{wardrobe_text}\n\n"
            "Suggest 1–2 complete outfits using the new item paired with specific pieces "
            "from the wardrobe above. Name the exact wardrobe pieces in each outfit. "
            "Keep each suggestion to 2–3 sentences.\n\n"
            "IMPORTANT: if none of the wardrobe pieces are compatible with the new item, "
            "reply with exactly the single word: NO_COMPATIBLE_OUTFIT"
        )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )

    content = response.choices[0].message.content
    if "NO_COMPATIBLE_OUTFIT" in content:
        return None

    return content


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
    if not outfit or not outfit.strip():
        return "Error: no outfit suggestion available — cannot generate a fit card."

    client = _get_groq_client()

    prompt = (
        "You are writing an Instagram/TikTok OOTD caption for someone who just thrifted a new piece.\n\n"
        f"Thrifted item: {new_item['title']} — ${new_item['price']} on {new_item['platform']}\n"
        f"Item description: {new_item['description']}\n\n"
        f"Outfit: {outfit}\n\n"
        "Write a 2–4 sentence caption that:\n"
        "- Feels casual and authentic, like a real OOTD post (not a product description)\n"
        "- Mentions the item name, price, and platform naturally, each exactly once\n"
        "- Captures the specific vibe of the outfit\n"
        "- Sounds fresh and personal\n\n"
        "Write only the caption — no labels, no hashtags, no preamble."
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=1.4,
    )

    return response.choices[0].message.content
