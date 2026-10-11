# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:** parsing, search and the branch are plain code and take
the same path every run, but two model calls come after them. On any one try
a call can come back empty or run out of rate-limit retries. One bad try in
five is the service; two would mean my code isn't handling it.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:** nothing before the branch calls the model. The query is
parsed with regex and the search is a filter over a fixed file, so the same
query stops in the same place every time. One miss would be a bug, not
chance.

---

## 3. The item search picked is the item every tool gets

For a matching query, the item `suggest_outfit` and `create_fit_card` receive
(their `in:` lines in the trace) has the same title and price as
`session["selected_item"]`, and that is `session["search_results"][0]`. All
three places agree in 5 of 5 tries.

**Why this target:** the hand-off is one dict passed through the session, with
no model and nothing random in between. A wrong index or a stale variable
would fail every run, not some, so anything under 5 of 5 is a bug.

---

## 4. The fit card has the facts, at caption length

For a matching query run 5 times, at least 4 of the 5 fit cards do all of:
contain the item's price written as `$N`, name its platform, stay at 60 words
or fewer, and never contain the word "None".

**Why this target:** the card comes from the model at temperature 0.9, so the
wording changes every try and it can drop one rule even though the prompt
states all four. One slip in five is tolerable for a caption; two would mean
the prompt isn't controlling it. "None" matters because 32 of 40 listings have
no brand.

---

## 5. A near miss says which filter to loosen

For `graphic tee under $15` (graphic tees exist, but the cheapest is $18), the
agent stops before `suggest_outfit`, and its message names price as the
problem and gives the cheapest matching price, in 5 of 5 tries.

**Why this target:** the message is built by code from the data, with no model
call, so the same query gets the same message every time. "No results" would
leave the user guessing which of three filters to change.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
