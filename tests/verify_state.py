"""
verify_state.py

Runs one complete FitFindr interaction using the example query from the
planning.md walkthrough and verifies that state is threaded correctly through
the session:

  - the dict `suggest_outfit` receives IS the same object as session["selected_item"]
  - the string `create_fit_card` receives IS session["outfit_suggestion"]

It does this by wrapping the two tools to record exactly what they were called
with, then comparing those captured arguments to the final session dict.

Run with (from the project root):
    python tests/verify_state.py
"""

import os
import sys

# Allow running directly from the tests/ folder by putting the project root
# (the parent of this file's directory) on the import path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent
from utils.data_loader import get_example_wardrobe

# Example query from the planning.md "A Complete Interaction" walkthrough.
QUERY = (
    "I'm looking for a vintage graphic tee under $30. I mostly wear baggy "
    "jeans and chunky sneakers. What's out there and how would I style it?"
)

# Capture what each tool actually receives at call time.
captured = {}

_real_suggest_outfit = agent.suggest_outfit
_real_create_fit_card = agent.create_fit_card


def _spy_suggest_outfit(new_item, wardrobe):
    captured["suggest_outfit_item"] = new_item
    return _real_suggest_outfit(new_item, wardrobe)


def _spy_create_fit_card(outfit, new_item):
    captured["create_fit_card_outfit"] = outfit
    return _real_create_fit_card(outfit, new_item)


# Patch the names the agent module looks up so the spies are used.
agent.suggest_outfit = _spy_suggest_outfit
agent.create_fit_card = _spy_create_fit_card

session = agent.run_agent(QUERY, get_example_wardrobe())

print("=" * 70)
print("QUERY:", QUERY)
print("=" * 70)
print("\nparsed:", session["parsed"])
print("\nsession['selected_item']:")
print(session["selected_item"])
print("\nsession['outfit_suggestion']:")
print(session["outfit_suggestion"])
print("\nsession['fit_card']:")
print(session["fit_card"])

print("\n" + "=" * 70)
print("STATE-PASSING CHECKS")
print("=" * 70)

# 1. The item suggest_outfit received must be the exact same object stored in
#    session["selected_item"] (identity, not just equality).
same_item = captured["suggest_outfit_item"] is session["selected_item"]
print(
    f"\n[1] selected_item passed into suggest_outfit is the same dict: {same_item}"
    f"\n    id(session['selected_item'])        = {id(session['selected_item'])}"
    f"\n    id(arg suggest_outfit received)     = {id(captured['suggest_outfit_item'])}"
)

# 2. The outfit string create_fit_card received must be exactly what
#    suggest_outfit produced and stored in session["outfit_suggestion"].
same_outfit = captured["create_fit_card_outfit"] is session["outfit_suggestion"]
print(
    f"\n[2] outfit_suggestion passed into create_fit_card is the same string: {same_outfit}"
    f"\n    id(session['outfit_suggestion'])    = {id(session['outfit_suggestion'])}"
    f"\n    id(arg create_fit_card received)    = {id(captured['create_fit_card_outfit'])}"
)

assert same_item, "selected_item was NOT the same dict passed into suggest_outfit"
assert same_outfit, "outfit_suggestion was NOT what was passed into create_fit_card"
print("\nAll state-passing checks PASSED ✅")
