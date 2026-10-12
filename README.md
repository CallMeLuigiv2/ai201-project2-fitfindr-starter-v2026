# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->

FitFindr is for someone shopping secondhand. They type what they want in plain
words, like `vintage graphic tee under $30`. It searches 40 thrift listings,
picks the best match, suggests outfits using clothes they already own, and
writes a short caption they could post. If nothing matches, it stops and says
which part of the search to change: the words, the size, or the price.

---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Filters the 40 listings by price and size, then scores each by keyword overlap with the description: +2 per word found in the title, +1 in the style tags, +1 in the category. Filler words ("looking", "for", "a") are ignored, and a trailing "s" is dropped so "tees" matches "tee". Listings that score 0 are dropped. The description field isn't searched, because non-tees mention "tee" there.
- **Inputs:** `description` (str), e.g. "vintage graphic tee". `size` (str or None): both sizes are split into pieces on spaces, `/` and parentheses, ignoring case, and a listing matches when it has every piece asked for, so "S" matches "S/M" but not "US 9". One Size listings always match. None skips the filter. `max_price` (float or None): dollars, inclusive. None skips the filter.
- **Returns:** `list[dict]`, at most 10 listing dicts (`config.SEARCH_RESULT_LIMIT`), highest score first, cheapest first on a tie. Each dict has `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand` (str or None), `platform`.
- **When it has nothing:** returns `[]`, never None and never an exception. The loop branches on this.

### `suggest_outfit`

- **What it does:** Asks the model for one or two outfits built around the item.
- **Inputs:** `new_item` (dict), one listing from `search_listings`. `wardrobe` (dict) with an `items` list, which may be empty.
- **Returns:** `str`, non-empty, under about 120 words. Each outfit names at least two wardrobe pieces by their exact `name`. Empty fields (brand None, missing notes) are left out of the prompt.
- **When it has nothing:** with an empty wardrobe, it asks for general styling ideas using common pieces instead. If the model sends back nothing, it returns a one-line fallback suggestion, never `""`.

### `create_fit_card`

- **What it does:** Asks the model for a first-person caption someone would post about the find.
- **Inputs:** `outfit` (str), the output of `suggest_outfit`. `new_item` (dict), the same listing.
- **Returns:** `str`, 2 to 4 sentences, under 60 words, no hashtags. It mentions the item, the price written as `$18`, and the platform, once each. A brand is only mentioned if the listing has one; 32 of 40 don't.
- **When it has nothing:** if `outfit` is empty or whitespace, it returns "Can't write a fit card: there's no outfit suggestion for this item yet." and doesn't call the model.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in
`session["error"]` naming which filters (words, size, price) ruled everything
out, and stop without calling `suggest_outfit`. Otherwise take the first result
as `session["selected_item"]` and go to `suggest_outfit`, then `create_fit_card`.

**Where it lives:** `agent.py::run_agent`. The stop message is built by
`agent.py::_why_empty`.

**How the query is parsed:** regex, in `agent.py::_parse_query`. "under $30" or
"$30" becomes `max_price`, "size M" becomes `size`, and the leftover words minus
filler become `description`.

**What moves through the session:** `query` → `parsed` → `search_results` →
`selected_item` (always `search_results[0]`) → `outfit_suggestion` → `fit_card`.
On the empty path, `error` is set and the last three stay `None`.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30'

  Found:    Vintage Band Tee — Faded Grey — $19.0 on depop

  Outfit:   Hey friend! That faded grey band tee is a thrift store holy grail. Here are two ways to style it using pieces you already own.

For an effortless grunge look, tuck the tee into your baggy straight-leg jeans, dark wash. Cinch your waist with the brown leather belt, and finish the outfit with your black combat boots and black crossbody bag. It is total 90s off-duty cool.

If you want to lean into streetwear, layer the tee over your white ribbed tank top so the white hem peeks out at the bottom. Pair it with your wide-leg khaki trousers, throw on your black cropped zip hoodie unzipped over top, and step into your chunky white sneakers. Happy thrifting!

  Fit card: Scored this perfectly faded vintage band tee for just $19 and it is peak grunge streetwear. The charcoal wash has the best lived-in feel. Find it live on my depop right now!
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print([(x['title'], x['size'], x['price']) for x in search_listings('graphic tee', max_price=30)])"
[('Graphic Tee — 2003 Tour Bootleg Style', 'L', 24.0), ('Y2K Baby Tee — Butterfly Print', 'S/M', 18.0), ('Vintage Band Tee — Faded Grey', 'L', 19.0), ('Vintage Graphic Hoodie — Faded Black', 'L', 26.0)]
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
For an easy everyday look, pair your vintage Levi's with the white ribbed tank top tucked in. Add the brown leather belt to define the waist and finish with your chunky white sneakers for a classic, effortless streetwear vibe.

For cooler weather, try a relaxed streetwear look by layering the oversized grey crewneck sweatshirt right over the jeans. Slip on your black combat boots and toss on the black crossbody bag to keep your hands free while you hunt for more thrift treasures.
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Scored these vintage Levi's 501 jeans for just $38 and I am obsessed. The medium wash indigo denim has the ultimate casual streetwear vibe. I am just wearing them with fresh white sneakers for an effortless look I found on depop.
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

I had claude write the code for tools.py and agent.py after, long discussions 
of reading the repo, discussing some things that could be found through the examples,
what to wathc out for and probe. this allowed us to plan affectively. i told it my intentions 
and it helped me draft the criteria and code. this made the planning for this assignment alot longer
than intended but made the iteration fast when things were set in place. hence the quick commits. 

**Moment 1**

- *What I asked for:* which listing fields `search_listings` should match
  keywords against. My plan was category and style_tags only.
- *What came back:* "jacket" isn't in any category or style tag, only in
  titles, so "denim jacket" would score denim jeans the same as the jacket.
  Two non-tees (`lst_011`, `lst_017`) also mention "tee" in their descriptions.
- *What I changed:* I added the title, weighted double, and kept description out.

**Moment 2**

- *What I asked for:* a size rule. Mine was an exact match, so "S" only matches "S".
- *What came back:* 3 listings are "S/M", which my rule hides from a size-S
  shopper, and the starter says "M" should match "S/M". A substring test is
  wrong too, because `"s" in "us 9"` is True.
- *What I changed:* sizes are split into pieces on spaces, `/` and
  parentheses, and only whole pieces match. One Size always matches.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The item search picked is the item every tool gets | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. The fit card has the facts, at caption length | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. A near miss says which filter to loosen | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

Full log: `results/run_2026-10-11_2049_before.md`. The empty-wardrobe run is
in there too as a diagnostic. It finished 5 of 5 with general styling ideas.

**Real output from one try**, pasted as text, naming the file and function
that produced it:

Criterion 1, try 4. Run by `run_eval.py::main`, loop in `agent.py::run_agent`,
card from `tools.py::create_fit_card`.

```
[1] parse_query
      in:  vintage graphic tee under $30
      out: description='vintage graphic tee', size=None, max_price=30.0
[2] search_listings (via MCP)
      in:  description='vintage graphic tee', size=None, max_price=30.0
      out: 10 items: Vintage Band Tee — Faded Grey, Graphic Tee — 2003 Tour Bootleg Style, Vintage Graphic Hoodie — Faded Black … +7 more
      →    branch: 10 found, taking the first
[3] suggest_outfit
      in:  Vintage Band Tee — Faded Grey ($19.0, depop)
      out: Hey thrift friend! For an effortless grunge look, tuck your vintage band tee into the baggy straight-leg jeans…
      →    wardrobe has 10 items
[4] create_fit_card
      in:  Vintage Band Tee — Faded Grey ($19.0, depop)
      out: Scored this perfectly faded grey vintage band tee for just $19. It has that ultimate grunge feel and I just li…

Fit card:
Scored this perfectly faded grey vintage band tee for just $19. It has that ultimate grunge feel and I just listed it on my depop. Grab it before it is gone!
```

It passes criterion 1, but read the card: it's written by someone selling the
tee, not someone who bought it. More on that below.

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | Matching query completes | 4 of 5 | MET (5/5) | Every trace reached step 4, `create_fit_card`, and every session had a fit card. |
| 2 | Impossible query stops early | 5 of 5 | MET (5/5) | Every trace stopped at step 2 with "branch: empty". `suggest_outfit` never ran, and the message said to change the words and the price. |
| 3 | Picked item = item every tool gets | 5 of 5 | MET (5/5) | In every try the first search result, `selected_item`, and both tools' `in:` lines were the 90s Track Jacket at $45.0. |
| 4 | Fit card facts and length | 4 of 5 | MET (5/5) | All five slip dress cards had "$30" and "depop", were 31 to 41 words, and never said "None". |
| 5 | Near miss names the filter | 5 of 5 | MET (5/5) | Every try stopped at step 2 and said the cheapest graphic tee is $18. |

**Diagnoses**

No criterion missed. But reading the cards turned up a problem none of them
check: **6 of 20 fit cards are written like the seller, not the buyer.** "I just
listed it on my depop. Grab it before it is gone!" Three were in the graphic
tee row and three in the empty-wardrobe row ("Score this vintage Wrangler denim
jacket for just $42 on poshmark and your streetwear style is instantly sorted"). The track jacket and slip dress cards were fine.

- **Where:** the model's output. Search, the loop and the session handed over
  the right item every time (criterion 3 shows it).
- **Why:** the prompt in `tools.py::create_fit_card` gives the model the price
  and the platform and says to mention both, but never says the person posting
  bought the item. Depop and Poshmark are apps people sell on, so an item, a
  price and "on depop" reads like a listing, and the model sometimes writes one.



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
