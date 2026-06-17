"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── query parser ─────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """
    Extract description, size, and max_price from a natural language query
    using regex. Returns a dict with keys: description, size, max_price.
    """
    # max_price: "under $30", "$30", "under 30"
    price_match = re.search(r'under\s+\$?(\d+(?:\.\d+)?)', query, re.IGNORECASE)
    if not price_match:
        price_match = re.search(r'\$(\d+(?:\.\d+)?)', query, re.IGNORECASE)
    max_price = float(price_match.group(1)) if price_match else None

    # size: explicit "size M" first, then bare size tokens (longest patterns first)
    size_match = re.search(r'\bsize\s+([A-Za-z0-9/]+)', query, re.IGNORECASE)
    if not size_match:
        size_match = re.search(r'\b(XXS|S/M|M/L|L/XL|XXL|XS|XL|[SML])\b', query, re.IGNORECASE)
    size = size_match.group(1).upper() if size_match else None

    # description: strip price, size, and filler phrases to get the item keywords
    desc = re.sub(r'under\s+\$?\d+(?:\.\d+)?', '', query, flags=re.IGNORECASE)
    desc = re.sub(r'\$\d+(?:\.\d+)?', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'\bsize\s+[A-Za-z0-9/]+', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'\b(XXS|S/M|M/L|L/XL|XXL|XS|XL|[SML])\b', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r"\b(looking for|i'm|i am)\b", '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'[,\.!?]+', ' ', desc)
    desc = ' '.join(desc.split())

    return {"description": desc or query, "size": size, "max_price": max_price}


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.
    """
    # Step 1: initialise session
    session = _new_session(query, wardrobe)

    # Step 2: parse the query into structured parameters
    session["parsed"] = _parse_query(query)
    description = session["parsed"]["description"]
    size        = session["parsed"]["size"]
    max_price   = session["parsed"]["max_price"]

    # Step 3: search — early return if nothing matches
    results = search_listings(description, size=size, max_price=max_price)
    session["search_results"] = results

    if not results:
        session["error"] = (
            "No listings found. Please try a different description, size, or price."
        )
        return session

    # Step 4: select the top result
    session["selected_item"] = results[0]

    # Step 5: suggest an outfit
    session["outfit_suggestion"] = suggest_outfit(session["selected_item"], wardrobe)

    # Step 6: create the fit card only when we have an outfit suggestion
    if not session["outfit_suggestion"]:
        session["error"] = (
            "Your wardrobe does not have enough compatible pieces yet. "
            "Try adding more wardrobe items or continue shopping."
        )
        return session

    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"], session["selected_item"]
    )

    # Step 7: return completed session
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
