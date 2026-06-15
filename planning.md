# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
This tool will take a product description, size, and price as input and return a list of product listings that best match the input. Given listings are retrieved by the load_listings() method from utils/data_loader.py, this tool will use size and max price to filter throught he catalog and then obtain relavence scores for each remaining product by keyword matching with the input description.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): Keywords describing what the user is looking for (e.g., "vintage graphic tee").
- `size` (str): Size string to filter by, or None to skip size filtering. Matching is case-insensitive (e.g., "M" matches "S/M").
- `max_price` (float): Maximum price of product listing (inclusive), or None to skip price filtering.

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
A list of matching listing dicts, sorted by relevance (best match first). Each listing dict contains the feilds id, title, description, category, style_tags, size, condition, price, colors, brand, and platform, in line with that of the listings.json file.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
The tool returns an empty list if nothing matches and does not raise an exception.
---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
This tool takes in a listing and user wardrobe to create an outfit that they could put together with the new item. This tool calls an LLM, specifically Groq's `llama-3.3-70b-versatile`.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): A listing dict (the item the user is considering buying). This dict will include the feilds id, title, description, category, style_tags, size, condition, price, colors, brand, and platform.
- `wardrobe` (dict): A wardrobe dict with an 'items' key containing a list of wardrobe item dicts.

**What it returns:**
<!-- Describe the return value -->
A non-empty string with outfit suggestions based on the item and peices in their wardrobe.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
This may occur in the case that the wardrobe is empty and the tool will instead offer general styling advice for the item rather than raising an exception or returning an empty string.


---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
This tool takes an outfit and listing calling the LMM to craft a usable, social media caption based on them.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): The outfit suggestion string from suggest_outfit().
- `new_item` (dict): A listing dict (the item the user is considering buying). This dict will include the feilds id, title, description, category, style_tags, size, condition, price, colors, brand, and platform.

**What it returns:**
<!-- Describe the return value -->
A 2–4 sentence string usable as an Instagram/TikTok caption.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
In the case that `outfit` is empty or missing, the returns a descriptive error message string and does not raise an exception.
---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->
The agent always starts with the search_listing tool. After search_listings runs, check if results is empty. If yes, set an error message in the session and return early. If no, set selected_item = results[0] and proceed to suggest_outfit. After suggest_outfit runs pass on the string as input alongside the dict returned by search_listings to lastly call create_fit_card.

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

Values are stored in the `session` dict created by `_new_session(query, wardrobe)`. Each step reads what it needs from the session and writes its result back, so the tools only depend on this dict. The helper function `_parse_query` fills value of key `parsed` (`description`, `size`, `max_price`), which is unpacked as the arguments to `search_listings`. Then, the result is stored in another pair with key `search_results`, and its first (most relevant) entry becomes `selected_item`. `selected_item` and `wardrobe` are used by `suggest_outfit`, whose string becomes `outfit_suggestion`. Finally, `outfit_suggestion` and `selected_item` are used as input for `create_fit_card`, whose string becomes `fit_card`.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | |
| suggest_outfit | Wardrobe is empty | |
| create_fit_card | Outfit input is missing or incomplete | |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->
     User query
     │
     ▼
     Planning Loop ───────────────────────────────────────────┐
     │                                                        │
     ├─► search_listings(description, size, max_price)        │
     │       │ results=[]                                     │
     │       ├──► [ERROR] "No listings found..." → return     │
     │       │                                                │
     │       │ results=[item, ...]                            │
     │       ▼                                                │
     │   Session: selected_item = results[0]                  │
     │       │                                                │
     ├─► suggest_outfit(selected_item, wardrobe)              │
     │       │                                                │
     │   Session: outfit_suggestion = "..."                   │
     │       │                                                │
     └─► create_fit_card(outfit_suggestion, selected_item)    │
               │                                              │
          Session: fit_card = "..."                           │
               │                                              └─ error path returns here
               ▼
          Return session

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**
For each tool, I will provide Claude with my tool spec outlined in the planning.md doc as well as the doc strings provided in tools.py for extra implentation instruction. I will also refer it to the architecture diagram, planning loop, and error handling sections of planning.md so that it knows how each tool should work in tandem with the others.

I expect Claude to return each tool completely realized and in a way that they can work to fit the agent's needs. I will verify this by reading through each provided implentation making sure inputs are being utilized accurately and tool will produce expected output.

**Milestone 4 — Planning loop and state management:**
I provided Claude with my planning loop and state management specifications as well as refered it the doc string found in agent.py to implement run_agent. I also specificed that I would liek to do parsing via regex. I anticipated it would need to build some helper functions for parsing at least and implement a complete function to run the agent step by step. I verified the accuracy of Claude's code through testing suites, both provided and personally added.
---

## A Complete Interaction (Step by Step)

<!-- Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query. -->

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->
First, the agent will derive the item of interest from the user query. It will use this as inout to call the `search_listings` tool.

**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->
The tool call from step 1 returns the three listings most relavent to the product described by the user. In this scenario that migth be "Faded Band Tee — $22, Depop, Good condition." Next, the agent will pick the best one and call `suggest_outfit` to retieve a possible outfit based on the listing selected and the user's wardrobe. Something along the lines of "Pair this with your wide-leg jeans and platform Docs for a classic 90s grunge look. Roll the sleeves once and tuck the front corner slightly for shape."

**Step 3:**
<!-- Continue until the full interaction is complete -->
Lastly, `create_fit_card` tool is called taking the outputted fit and selected listing from step two to create a social media caption for the outfit. An example caption in this scenario would be: "thrifted this faded band tee off depop for $22 and honestly it was made for my wide-legs 🖤 full look in my stories".

**Final output to user:**
<!-- What does the user actually see at the end? -->
In the end, the user will get a complete answer which will include a listing that matches the product they are looking for, an outfit idea based on this find and thier own wardrobe, and finally the perfect caption for the whole fit.