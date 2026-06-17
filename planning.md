# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

### Tool 1: search_listings

**What it does:**
search_listings takes in a desired article of clothing, size, and maximum price. This function narrows down the possible clothing pieces to output to the top 3.


**Input parameters:**
- `description` (str): preferred article of clothing
- `size` (str): user's size
- `max_price` (float): maximum price of the clothing item

**What it returns:**
This function returns a list containing the top 3 search results, sorted in order of relevance.

**What happens if it fails or returns nothing:**
This means that there are no relevant clothing items that fit the user's search terms and the user is told to try searching again differently.

---

### Tool 2: suggest_outfit

**What it does:**
This function suggests an outfit using the user's newly suggested article of clothing and the user's existing wardrobe of clothes.

**Input parameters:**
- `new_item` (dict): the item the user just got suggested
- `wardrobe` (dict): the user's existing wardrobe with item dicts inside

**What it returns:**
This function returns a string suggesting a possible outfit.

**What happens if it fails or returns nothing:**
If no outfit can be created, the user is informed that they do not have compatible pieces to pair their new piece with, and are encouraged to continue shopping. If the user's wardrobe is empty, they are given general styling ideas for the new item.
---

### Tool 3: create_fit_card

**What it does:**
This function takes an outfit and the new item and returns a short and sharable outfit caption (to share on social media perhaps).

**Input parameters:**
- `outfit` (str): the outfit suggested by suggest_outfit
- `new_item` (dict): the new clothing item the user got suggested

**What it returns:**
This function returns a short, sharable caption of the new outfit and new item as a string

**What happens if it fails or returns nothing:**
An error message is displayed. This function should not be run if the user is not given an outfit.

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->
1. The user submits a user query detailing their preferred article of clothing, their size, and their maximum price.

2. search_listing gets called. It looks for compatible clothing items given the user's query. If no items are found, the user is informed so and is asked to try searching again differently. Otherwise, the top 3 compatible items are returned and FitFindr selects the top item.

3. suggest_outfit gets called. It aims to suggest an outfit for the user based on the new item and wardrobe. If the user has no compatible items to pair the new item with, the user is told to retry their search. If the user's wardrobe is empty, the user is given general styling ideas. Otherwise, the outfit is suggested normally.

4. create_fit_card gets called. It outputs a catchy and short caption based on the outfit suggested. If no outfit was suggested, this function should not run.


---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->
The agent stores state in a session dictionary (called session). After each tool is run, the important information is stored in the session dictionary for later use.
The following data is tracked:
- past user querries
- the current user query
- top 3 search results from search_listings
- the selected item chosen by FitFindr
- the user's wardrobe
- the user's suggeted outfit from suggest_outfit
- the final fit card returned by create_fit_card

After `search_listings` finds matching items, the agent stores `session["selected_item"] = results[0]`. Then `suggest_outfit` reads that selected item and wardrobe. After that, the outfit suggestion is stored in `session["outfit_suggestion"]`, and `create_fit_card` uses both `session["outfit_suggestion"]` and `session["selected_item"]` to generate the final caption.

If search returns no results, the session stores empty information and an error message is thrown. The agent stops early instead of calling the later tools with missing data.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query |The user is told to search again|
| suggest_outfit | Wardrobe is empty |The user is given general styling ideas|
| suggest_outfit | Wardrobe has no compatible items |The user is told to retry their search|
| create_fit_card | Outfit input is missing or incomplete |N/A: This function does not run with empty or incomplete input|

---

## Architecture

User query
    │
    ▼
Planning Loop
    │
    │  Extract description, size, and max_price from user query
    │
    ▼
search_listings(description, size, max_price)
    │
    ├── results == []
    │       │
    │       ▼
    │   Session:
    │     search_results = []
    │     selected_item = None
    │     outfit_suggestion = None
    │     fit_card = None
    |
    │   Print: "No listings found. Please try a different description, size, or price."
    |   Return None
    │   NOTE: suggest_outfit and create_fit_card do not run.
    │
    └── results != []
            │
            ▼
        Session:
          search_results = results
          selected_item = results[0]
            │
            ▼
suggest_outfit(selected_item, wardrobe)
    │
    ├── no compatible outfit can be created
    │       │
    │       ▼
    │   Session:
    │     outfit_suggestion = None
    │     fit_card = None
    │
    |   Print: "Your wardrobe does not have enough compatible pieces yet. Try adding more wardrobe items or continue shopping."
    │   Return None
    │   NOTE: create_fit_card does not run because there is no complete outfit.
    |
    ├── wardrobe is empty
    │       │
    │       ▼
    │   Session:
    │     outfit_suggestion = outfit_suggestion
    │   NOTE: general styling ideas for the item are given
    │
    └── outfit_suggestion is valid
            │
            ▼
        Session:
          outfit_suggestion = outfit_suggestion
            │
            ▼
create_fit_card(outfit_suggestion, selected_item)
    │
    ├── outfit_suggestion is empty OR selected_item is None
    │       │
    │       ▼
    │   Session:
    │     fit_card = None
    │     ERROR
    │
    │   Return session
    │
    └── fit_card is valid
            │
            ▼
        Session:
          fit_card = fit_card
          error = None
            │
            ▼
        Return session to user



---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**
I plan to use Claude to help implement each tool one at a time. For each tool, I will give Claude the matching tool spec from this planning.md, including the function name, input parameters, expected return value, and failure mode.

For `search_listings`, I will provide the spec and ask Claude to implement `search_listings(description, size, max_price)` using `load_listings()` from `utils/data_loader.py`. I expect it to produce code that filters listings by description, size, and maximum price, returns the top 3 matching item dictionaries, and returns an empty list if no matches are found. I will verify the output by testing it with a query that should return results, a query that should return no results, and a query with a strict price.

For `suggest_outfit`, I will provide the spec and ask Claude to implement `suggest_outfit(new_item, wardrobe)` using Groq. I expect it to produce a string with a complete outfit suggestion using the selected item and the user's wardrobe. I will verify that it handles a normal wardrobe, an empty wardrobe, and an incompatible wardrobe.

For `create_fit_card`, I will provide the spec and ask Claude to implement `create_fit_card(outfit, new_item)` using Groq. I expect it to produce a short, shareable outfit caption. I will verify that it returns a good caption for valid input and returns an error message if the outfit input is empty. I will also run it multiple times to make sure the captions are not always identical.

Before moving on, I will run pytest tests for each tool and confirm that each required failure mode is handled.

**Milestone 4 — Planning loop and state management:**

I plan to use Claude to help implement the planning loop in `agent.py`. I will give it the Planning Loop section, the State Management section, and the Architecture diagram from this planning.md.

I expect it to produce code for `run_agent()` that calls the tools conditionally instead of always running all three tools. The agent should call `search_listings` first, store the results in the session dictionary, and stop early if no results are found. If results exist, it should store `session["selected_item"] = results[0]` and then call `suggest_outfit`. If a complete outfit is created, it should store the outfit suggestion and then call `create_fit_card`. If the outfit is missing or incomplete, it should stop before calling `create_fit_card`.

I will verify the planning loop by running one successful query that uses all three tools and one failure query where `search_listings` returns no results. In the failure case, I will check that an error message is printed and that `suggest_outfit` and `create_fit_card` do not run. I will also inspect the session dictionary to confirm that state is being passed correctly between tool calls.



---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent first searches using search_listings("vintage graphic tee", size="M", max_price = 30.0) and this function returns the top 3 matching listings. The top result is chosen.

**Step 2:**
Step 1 returns the top 3 search results (items that are most relevant to user's search terms) and then suggest_outfit(new_item=<new item>, wardrobe = <user's wardrobe>) is called. This function suggests an outfit using the new item and the user's existing wardrobe.

**Step 3:**
Step 2 returns a suggested outfit based on the new item and existing wardrobe. Next, a fit card is created using create_fit_card(outfit=<suggestion>, new_item=<new item>).

**Final output to user:**
Step 3 returns a fit card using the new item, so the user finally sees this fit card with the full outfit using the new item and their wardrobe (full styled look).
