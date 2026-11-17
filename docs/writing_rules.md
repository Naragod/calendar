# Writing rules

Apply to UI copy, error messages, help text, READMEs, and any prose deliverable. Code rules live in `CLAUDE.md`.

## Priority: clarity beats brevity

Clarity is the goal. Brevity serves clarity, not the other way around.

The shortest draft that delivers the fact **and lands on the first read** wins. Not the absolutely shortest draft. If a cut forces the reader to reread, restore it. If verbosity is needed for clarity, apply it: a concrete example, a code snippet, a contrast (`not X — Y`), or a vivid framing all earn their words when they help the reader understand on the first pass.

The eleven rules below sit underneath this one. When a rule and clarity conflict, clarity wins, and the rule bends.

## The eleven rules

### 1. Lead with the answer
The first sentence of every section states the conclusion. A reader who stops there still has the point. When the goal is an answer or action, ask it as a direct question — "How do we generate a service key?" beats a soft statement or "we ask for your help."

### 2. Concrete over abstract
"Cuts cold start from 800 ms to 120 ms." Not "improves performance." "1,400 rows." Not "many rows."

### 3. Active voice
"The parser rejects the row." Not "the row is rejected by the parser."

### 4. Plain words
`use` not `utilize`. `help` not `facilitate`. `about` not `regarding`. `send` not `transmit`.

### 5. Present tense
"The parser halts." Not "the parser will halt." Future tense only for events that have not happened yet.

### 6. One claim per bullet
A bullet joined by `and`, `;`, or `—` is two bullets. Split.

### 7. No editorializing
State the fact, let the reader judge. Banned words below.

### 8. Cut until removing one more word loses information *or* clarity
Remove the sentence. Re-read. If the meaning survives **and the sentence still lands on first read**, the deletion stays. Stop when the next deletion loses meaning, or when the result forces a reread. The right length delivers the fact cleanly. Often shorter than the first draft. Sometimes longer — when a concrete example or contrast earns its words. In a request, cut mission or values lines that skip past the ask; let the real question carry the point.

### 9. Strong verbs and nouns over weak ones with modifiers
Pick the one word that carries the meaning. "Jeff sprinted across the gym." Not "Jeff moved swiftly across the training grounds." A weak verb propped up with an adverb is a stronger verb waiting. A formal noun is a common one in disguise.

### 10. Grade 8 reading level ceiling
A teenager reads the draft and gets it. Pick the shorter word when a shorter one works (`use` not `utilize`, `next` not `subsequent`). Keep sentences under 20 words on average. Break a sentence with two ideas into two sentences. No nested clauses.

### 11. Speak in the positive
Say what can happen, not what can't. Frame every point toward the path forward. Turn a limit into a forward question: replace "I cannot do X" with "Can we do Y instead?" A dead-end becomes a next step. Drop "only".

## Banned words

| Category | Examples |
|---|---|
| Editorializing adjectives | interesting, important, key, critical, essential, natural, right, useful, simple, obvious |
| Hedges | roughly, basically, fundamentally, in essence, arguably, somewhat, fairly |
| Filler intensifiers | very, really, quite, rather, just, actually, simply, truly |
| Clichés | load-bearing, north star, chokepoint, guardrail, low-hanging fruit, moving the needle, at the end of the day |
| Recap openers | bottom line, in summary, to wrap up, all in all, that said |
| Throat-clearing | it should be noted, it is worth mentioning, needless to say, of course |
| Future-tense facts | will be, will go, will halt, is going to → present tense |
| Weak verbs | need, needs → requires, must |
| Long words when short ones fit | utilize → use, subsequent → next, demonstrate → show, sufficient → enough, terminate → end, prior to → before, in order to → to |
| Limiting / negative framing | only; can't / cannot → reframe as "can we do Y instead?" (Rule 11) |

Scan every draft for these. Each hit gets rewritten or removed.

## Self-edit checklist

Walk the draft once. Each failed check is a rewrite, not a polish.

- [ ] First sentence of every section states the conclusion.
- [ ] No banned word from above appears (grep the file).
- [ ] Every point speaks to what can happen, not what can't. No "only"; a limit reads as "can we do Y?" (Rule 11).
- [ ] Every number cites a source or gets deleted.
- [ ] No bullet contains `and`, `;`, or `—`.
- [ ] No "Bottom line", "In summary", "TL;DR" unless the doc exceeds 1500 words.
- [ ] Each row of every table answers *so what?*, not *what is it?*
- [ ] Read each paragraph aloud. A stumble is a rewrite, not a polish.
- [ ] Sentences average under 20 words. Pick the next-shorter word when one fits.
- [ ] A draft within 2% of any word cap was padded. Cut again.
- [ ] Read each section once at reader-speed. If you had to reread to follow it, restore the cut you made — clarity beats brevity.
- [ ] Concrete examples, code snippets, and `not X — Y` contrasts stayed in when they earn their words.

## Examples — real revisions

| Before | After | Rule |
|---|---|---|
| "LiteLLM is the load-bearing scaffolding, not the product." | "LiteLLM provides the plumbing." | 4, 7 |
| "Building those is the interesting work." | (deleted) | 7 |
| "Every AI grading call MarkUs makes will go through one place we control." | "Every AI grading call from MarkUs goes through one proxy." | 3, 5 |
| "Rails 7's `encrypts` is the natural fit." | "Rails 7's `encrypts` macro applies." | 7 |
| "Pre-call / post-call hook system" | "Pre-call and post-call insertion points — saves a custom middleware framework" | 2 |
| Closing "Bottom line" paragraph that repeated earlier content | (deleted) | 8 |
| "Jeff moved swiftly across the training grounds." | "Jeff sprinted across the gym." | 9, 10 |
| "We will subsequently demonstrate that the proxy halts the call." | "The proxy halts the call." | 4, 5, 8, 10 |
| "It should be noted that the data is stored locally." | "Data stays on your machine." | 4, 7, 10 |
| "We are unable to find where to create one." | "Where in the dashboard do we create a service key?" | 1, 11 |
| "...which requires a service key." | "How do we generate a service key?" | 1 |
| "Only the search text leaves." | "The search text leaves; your numbers stay put." | 11 |

## Pushback patterns

- **No thesis named?** Read the source first. Identify the single load-bearing claim. The first paragraph drafted is the thesis.
- **Word cap?** Treat it as a ceiling. Stop when the content is complete. Padding to hit the cap fails rules 1 and 8.
