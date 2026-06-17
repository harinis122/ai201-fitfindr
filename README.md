# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows:**
```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Tool Inventory


name, inputs with parameter names and types, outputs, purpose
- Tool 1: search_listings(description: str, size: str | None, max_price: float | None) -> list[dict]
     - inputs: description: str, size: str | None, max_price: float | None
     - output: list[dict] which contains up to three relevant items from listing
     - purpose: get relevant clothing items from the listing based on the user's query
- Tool 2: suggest_outfit(new_item: dict, wardrobe: dict) -> str
     - inputs: new_item: dict, wardrobe: dict
     - output: str which contains the outfit suggestion
     - purpose: suggest an outfit to the user using the new item and pieces from their wardrobe
- Tool 3: create_fit_card(outfit: str, new_item: dict) -> str
     - inputs: outfit: str, new_item: dict
     - output: str which contains an authentic, casual OOTD caption for Instagram/TikTok
     - purpose: give the user a casual, social media-worthy way of showing off their outfit using their new item

---

## Planning Loop + State Management Approach

The planning loop is in run_agent() in agent.py. It runs the three tools **conditionally** since each tool only runs if the previous one gave usable output.

**Query parsing:** _parse_query() uses regex to extract a description (item keywords), an optional size, and an optional max_price from the user's query. Price and size tokens are stripped from the query text, and the rest of the query becomes the description passed to search_listings.

**Conditional tool calls:**
1. search_listings always runs first. If it returns [], the loop sets session["error"] and returns immediately. The LLM tools never run.
2. suggest_outfit runs only when search_results is not empty. If it returns None (incompatible wardrobe), the loop again sets session["error"] and stops before create_fit_card is run.
3. create_fit_card runs only when outfit_suggestion is a non-empty string.

**State management:** All results are stored in a single session dict initialised by _new_session() at the start of each call. The keys that flow between tools are:

| Key | Set by | Read by |
|-----|--------|---------|
| parsed | _parse_query | search_listings call |
| search_results | search_listings | agent loop (empty check) |
| selected_item | agent loop (results[0]) | suggest_outfit, create_fit_card |
| outfit_suggestion | suggest_outfit | agent loop (None check), create_fit_card |
| fit_card | create_fit_card | handle_query in app.py |
| error | agent loop (on any early exit) | handle_query in app.py |

handle_query in app.py inspects session["error"] first. If it is set, only the listing panel is populated with the error message and the remaining panels are left blank.

---

## Interaction Walkthrough

**User query:** "vintage graphic tee under $30"

**Step 1 — Tool called:**
- Tool: search_listings
- Input: description="vintage graphic tee", size=None, max_price=30.0
- Why this tool: The planning loop first parses the query with regex to extract the item keywords, optional size, and price ceiling, then calls search_listings to filter and rank the 40 mock listings. This is always the first tool because every other step depends on having this concrete item to work with.
- Output: A list of up to 3 matching listing dicts sorted by keyword-overlap score. The top result is **Y2K Baby Tee — Butterfly Print** ($18.00, size S/M, depop). The agent stores all three in session["search_results"] and puts the top item in session["selected_item"].

**Step 2 — Tool called:**
- Tool: suggest_outfit
- Input: new_item=<Y2K Baby Tee dict>, wardrobe=<example wardrobe with 10 items>
- Why this tool: Once an item is selected, the agent calls suggest_outfit to figure out how to wear it. The example wardrobe is not empty, so the tool formats each wardrobe piece into a readable list and asks the Groq llama-3.3-70b-versatile LLM to name specific combinations. The result is stored in session["outfit_suggestion"].
- Output: A 2–3 sentence outfit suggestion - e.g., "Pair the Y2K Baby Tee with the Baggy straight-leg jeans and Chunky white sneakers for a relaxed streetwear look. Layer the Vintage black denim jacket for a cool, edgy finish."

**Step 3 — Tool called:**
- Tool: create_fit_card
- Input: outfit=<outfit suggestion string>, new_item=<Y2K Baby Tee dict>
- Why this tool: With a confirmed outfit in hand, the agent calls create_fit_card to turn the raw suggestion into a casual, shareable caption. The LLM is prompted at temperature 1.4 to ensure the caption sounds casual. The result is stored in session["fit_card"].
- Output: A short OOTD caption — e.g., *"Just scored this Y2K Baby Tee for $18 on Depop and I'm obsessed. Paired it with my baggy straight-leg jeans and chunky white sneakers for the ultimate laid-back streetwear vibe."*

**Final output to user:** The Gradio UI populates three panels: the listing panel shows the item's title, price, size, condition, platform, style tags, colors, and description; the outfit panel shows the LLM's suggestion; the fit card panel shows the shareable caption ready to copy.

---

## Error Handling and Fail Points

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No listings match the description, size, or price filter — returns [] | run_agent sets session["error"] to *"No listings found. Please try a different description, size, or price."* and returns immediately. suggest_outfit and create_fit_card are never called. The Gradio UI puts the error in the listing panel and leaves the remaining two panels blank. |
| suggest_outfit | The wardrobe is not empty but none of the items are compatible with the new piece. LLM replies with NO_COMPATIBLE_OUTFIT | The function detects NO_COMPATIBLE_OUTFIT and returns None. run_agent checks if not session["outfit_suggestion"], sets session["error"], and stops before calling create_fit_card. If the wardrobe is empty, the function does not fail, it calls the LLM with a general styling prompt and returns this advice instead. |
| create_fit_card | The outfit argument is an empty or whitespace-only string | The function returns the string "Error: no outfit suggestion available — cannot generate a fit card." No exception is raised. In practice, this case is prevented by run_agent's guard on outfit_suggestion, but the tool handles it regardless. |

---

## Spec Reflection

**One way planning.md helped during implementation:**
Throughout implementation, planning.md helped because it had every single requirement, tool, and overall program state and their purposes spelled out so that I would rarely have to stop and think about what I wanted my program to do. Having planning.md before implementation allowed me to not have to worry about handling edge cases and getting lost in theory while implementing my program. This allowed me to be more efficient during implementation.

**One divergence from your spec, and why:**
One divergence from my spec was my way of handling an empty wardrobe. Originally, I was thinking to give the user a failure message saying that their wardrobe is empty and an outfit cannot be created, but after starting to implement my program, I realized that it would be better to inform the user of how their new piece can be used in an outfit. This is to make the user happy with their first item and think of the possibilities with it rather than disappointing them with a failure message.

---

## AI Usage
1. I gave Claude my architecture diagram and Tool 2 spec from planning.md and asked it to build out the suggest_output function. While it did a good job of handling the happy case, it treated an empty wardrobe as a failure case and outputted an error message and it did not handle an incompatible wardrobe case at all. I changed the suggest_outfit function to suggest possible outfits with the new item with an empty wardrobe and made sure that a failure message is outputted for an incompatible wardrobe case.

2. I gave Claude my Tool 3 spec and asked it to give me a good prompt to give Groq LLM to get a casual, genuine OOTD caption for the create_fit_card function. Although it did specify Groq to make the caption casual and social media-worthy, the resulting caption from Groq LLM was too lengthy because Claude did not specify a character cap. I added a 125 character cap to the Groq prompt so that the captions would be shorter.


---

## Where to Start

1. **Read planning.md and fill it out before writing any code.**
2. Verify the data loads correctly by running python utils/data_loader.py.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.
