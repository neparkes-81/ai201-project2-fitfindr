# FitFindr 

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

---

## Tool Inventory

| Tool | Inputs (name: type) | Output | Purpose |
|------|---------------------|--------|---------|
| `search_listings` | `description: str`, `size: str \| None`, `max_price: float \| None` | `list[dict]` — matching listing dicts sorted by relevance (best first); `[]` if nothing matches | Takes a product description, optional size, and optional price ceiling, filters the catalog by size/price, then scores the remaining listings by keyword overlap with the description. |
| `suggest_outfit` | `new_item: dict` (a listing), `wardrobe: dict` (has an `items` list) | `str` — a non-empty outfit suggestion | Calls Groq's `llama-3.3-70b-versatile` to build 1–2 outfits pairing the new item with named pieces from the user's wardrobe. |
| `create_fit_card` | `outfit: str`, `new_item: dict` (a listing) | `str` — a 2–4 sentence Instagram/TikTok caption | Calls the LLM to turn an outfit + item into a casual, shareable social-media caption that names the item, price, and platform. |

---

## Planning Loop

The agent always starts with the `search_listings` tool. After `search_listings` runs, it checks whether results is empty. If yes, it sets an error message in the session and returns early. If no, it sets `selected_item = results[0]` and proceeds to `suggest_outfit`. After `suggest_outfit` runs, it passes that string as input alongside the dict returned by `search_listings` to lastly call `create_fit_card`. Before any of this, the query is parsed (`_parse_query`) into a description, size, and max price, and an empty query short-circuits with an error.

---

## State Management

Values are stored in the `session` dict created by `_new_session(query, wardrobe)`. Each step reads what it needs from the session and writes its result back, so the tools only depend on this dict. The helper function `_parse_query` fills the value of key `parsed` (`description`, `size`, `max_price`), which is unpacked as the arguments to `search_listings`. Then, the result is stored in another pair with key `search_results`, and its first (most relevant) entry becomes `selected_item`. `selected_item` and `wardrobe` are used by `suggest_outfit`, whose string becomes `outfit_suggestion`. Finally, `outfit_suggestion` and `selected_item` are used as input for `create_fit_card`, whose string becomes `fit_card`. The `error` field starts as `None`; callers check it first to decide whether to show results or the error message.

---

## Error Handling

| Tool | Failure mode | Agent response |
|------|--------------|----------------|
| `search_listings` | No results match the query | Returns `[]` (never raises); the planning loop sets a descriptive `error` and returns early without running the LLM tools. |
| `suggest_outfit` | Wardrobe is empty | Detects the empty `items` list and asks the LLM for general styling advice instead of itemized outfits, so it still returns a non-empty string. |
| `create_fit_card` | Outfit input is missing or incomplete | Guards against an empty/whitespace `outfit` and returns a descriptive error string rather than raising. |
| `suggest_outfit` / `create_fit_card` | LLM/API call fails (missing key, network error, empty response) | `_chat` catches any exception and returns a usable fallback string, so the loop never crashes. |

**Concrete example from testing:** running the query `"designer ballgown size XXS under $5"` parsed to `{description: "designer ballgown", size: "XXS", max_price: 5.0}`. No listing matched, so `search_listings` returned `[]` and the planning loop returned early with:

> `No listings found matching 'designer ballgown', size XXS, under $5. Try loosening the size or price filters, or different keywords.`

The downstream `outfit_suggestion` and `fit_card` fields stayed `None`, confirming the LLM tools were never called on empty input. Separately, calling `create_fit_card("   ", item)` returned `"Can't write a fit card yet — no outfit suggestion was provided. Generate an outfit with suggest_outfit() first."`, confirming the empty-outfit guard.

---

## Spec Reflection

**One way the spec helped you during implementation:**
The planning.md spec acted as an explicit and detailed outline I could provide to Claude before writing any code. Because each tool's specifications were written down thouroghly in advance, the generated implementations matched what I anticipate.

**One way your implementation diverged from the spec, and why:**
My implementation went slightly beyond the original spec scope. So I simply backtracked and supplemented sections like state management in planning.md and error hanldling in my readme.

---

## AI Usage

**Instance 1**

- *What I gave the AI:*
I provided Claude the tool specs from the Tools section of planning.md, the docstrings in `tools.py`, and pointed it at the architecture diagram, planning loop, and error-handling sections so it understood how the three tools work together. I also had it inspect `data/listings.json` and `wardrobe_schema.json` for the real field shapes and size formats.

- *What it produced:*
It implemented all three tools: a pure-Python `search_listings` with token-based size matching and weighted keyword scoring, plus `suggest_outfit` and `create_fit_card` backed by Groq, sharing a `_chat` helper. It verified the work against `tests/test_tools.py` (3/3 passing) and live Groq calls.

- *What I changed or overrode:*
I directed it to make the LLM tools fail soft and catch any API error and returning a non-empty fallback string instead of raising so the agent loop stays robust even without a working key. I also had it use subset/token matching for sizes, as in "M" matches "S/M" but "XXS" matches nothing, rather than naive substring matching.

**Instance 2**

- *What I gave the AI:*
For the planning loop and UI, I gave Claude the `run_agent` docstring steps, the planning-loop description from planning.md, and the numbered TODO in `app.py`'s `handle_query`. I asked it to parse the query, thread state through the session, and wire the Gradio panels.

- *What it produced:*
It implemented `_parse_query` (regex for price/size), the full `run_agent` planning loop, and `handle_query`, then wrote `tests/verify_state.py` to prove (by object identity) that `selected_item` and `outfit_suggestion` are passed through the session unchanged.

- *What I changed or overrode:*
I asked it to move the verification script into `tests/` and add a `sys.path` insert so the imports still resolve when run from that folder. I also had it surface the parsed filters inside the no-results error message instead of returning a generic "not found".
