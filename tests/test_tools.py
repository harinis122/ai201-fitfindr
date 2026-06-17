from unittest.mock import MagicMock, patch

import pytest

from tools import create_fit_card, search_listings, suggest_outfit


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_item():
    return {
        "id": "lst_test",
        "title": "Y2K Baby Tee — Butterfly Print",
        "description": "A cute vintage-style baby tee with a butterfly graphic.",
        "category": "tops",
        "style_tags": ["y2k", "vintage", "graphic"],
        "size": "S/M",
        "condition": "good",
        "price": 18.0,
        "colors": ["white", "pink"],
        "brand": None,
        "platform": "depop",
    }


@pytest.fixture
def empty_wardrobe():
    return {"items": []}


@pytest.fixture
def example_wardrobe():
    return {
        "items": [
            {
                "id": "w_001",
                "name": "Baggy straight-leg jeans, dark wash",
                "category": "bottoms",
                "colors": ["dark blue", "indigo"],
                "style_tags": ["denim", "streetwear", "baggy"],
                "notes": "High-waisted, sits above the hip",
            },
            {
                "id": "w_002",
                "name": "Chunky white sneakers",
                "category": "shoes",
                "colors": ["white"],
                "style_tags": ["streetwear", "chunky"],
                "notes": None,
            },
        ]
    }


def _mock_groq_client(response_text: str):
    """Return a Groq client mock that yields response_text from the LLM."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices[0].message.content = response_text
    return mock_client


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    # Failure mode: no listings match → returns [], not an exception
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter():
    # Every returned item must have the requested size in its size field
    results = search_listings("top", size="M", max_price=None)
    for item in results:
        assert "M" in item["size"].upper()


def test_search_returns_at_most_three():
    results = search_listings("vintage", size=None, max_price=None)
    assert len(results) <= 3


def test_search_drops_zero_score_items():
    # A query with no matching keywords should return nothing even if price/size pass
    results = search_listings("zzznomatch", size=None, max_price=None)
    assert results == []


def test_search_returns_dicts_with_expected_keys():
    results = search_listings("jeans", size=None, max_price=50)
    required_keys = {"id", "title", "description", "category", "style_tags",
                     "size", "condition", "price", "colors", "platform"}
    for item in results:
        assert required_keys.issubset(item.keys())


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

@patch("tools._get_groq_client")
def test_suggest_outfit_empty_wardrobe_calls_llm(mock_get_client, sample_item, empty_wardrobe):
    # Failure mode: empty wardrobe — should still call LLM and return a non-empty string
    mock_get_client.return_value = _mock_groq_client("Great with high-waisted jeans and sneakers.")

    result = suggest_outfit(sample_item, empty_wardrobe)

    assert isinstance(result, str)
    assert len(result.strip()) > 0
    mock_get_client.return_value.chat.completions.create.assert_called_once()


@patch("tools._get_groq_client")
def test_suggest_outfit_with_wardrobe_calls_llm(mock_get_client, sample_item, example_wardrobe):
    # Happy case: non-empty wardrobe → LLM called, result is a non-empty string
    mock_get_client.return_value = _mock_groq_client("Pair with the baggy jeans and white sneakers.")

    result = suggest_outfit(sample_item, example_wardrobe)

    assert isinstance(result, str)
    assert len(result.strip()) > 0
    mock_get_client.return_value.chat.completions.create.assert_called_once()


@patch("tools._get_groq_client")
def test_suggest_outfit_empty_wardrobe_uses_general_prompt(mock_get_client, sample_item, empty_wardrobe):
    # The prompt sent for an empty wardrobe should not reference a wardrobe list
    mock_get_client.return_value = _mock_groq_client("General styling advice.")

    suggest_outfit(sample_item, empty_wardrobe)

    call_kwargs = mock_get_client.return_value.chat.completions.create.call_args
    prompt_text = call_kwargs[1]["messages"][0]["content"]
    assert "wardrobe is empty" in prompt_text.lower()


@patch("tools._get_groq_client")
def test_suggest_outfit_with_wardrobe_includes_items_in_prompt(mock_get_client, sample_item, example_wardrobe):
    # The prompt for a non-empty wardrobe should mention the actual wardrobe items
    mock_get_client.return_value = _mock_groq_client("Outfit suggestion here.")

    suggest_outfit(sample_item, example_wardrobe)

    call_kwargs = mock_get_client.return_value.chat.completions.create.call_args
    prompt_text = call_kwargs[1]["messages"][0]["content"]
    assert "baggy straight-leg jeans" in prompt_text.lower()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def test_create_fit_card_empty_outfit_returns_error(sample_item):
    # Failure mode: empty outfit string → error message, no exception
    result = create_fit_card("", sample_item)
    assert isinstance(result, str)
    assert "error" in result.lower()


def test_create_fit_card_whitespace_outfit_returns_error(sample_item):
    # Failure mode: whitespace-only outfit string → error message, no exception
    result = create_fit_card("   ", sample_item)
    assert isinstance(result, str)
    assert "error" in result.lower()


@patch("tools._get_groq_client")
def test_create_fit_card_happy_case(mock_get_client, sample_item):
    # Happy case: valid outfit → LLM called, returns non-empty string
    mock_get_client.return_value = _mock_groq_client("Just thrifted this gem on depop for $18!")

    result = create_fit_card("Baggy jeans and chunky sneakers.", sample_item)

    assert isinstance(result, str)
    assert len(result.strip()) > 0
    mock_get_client.return_value.chat.completions.create.assert_called_once()


@patch("tools._get_groq_client")
def test_create_fit_card_does_not_call_llm_on_empty_outfit(mock_get_client, sample_item):
    # Guard check: LLM must NOT be called when outfit is empty
    create_fit_card("", sample_item)
    mock_get_client.assert_not_called()
