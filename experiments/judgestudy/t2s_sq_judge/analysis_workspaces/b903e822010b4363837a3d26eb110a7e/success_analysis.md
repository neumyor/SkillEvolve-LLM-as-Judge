# Success Memory Item 1
## Title
Parse Dual-Hint Clue Structures
## Description
Recognize and decompose questions formatted as trivia or crossword clues that present two parallel descriptors for a single target term.
## Content
When a prompt uses phrasing like "Term for [Definition A], or what [Subject] are '[Quoted Phrase]'", treat it as a dual-hint puzzle. The first part establishes the literal domain category, while the second part provides a linguistic shortcut. Decompose the prompt into these two components and search for a single word that simultaneously satisfies both conditions.

# Success Memory Item 2
## Title
Complete Quoted Phrases via Common Collocations
## Description
Use explicitly quoted fragments to trigger standard idioms or fixed phrases that naturally contain the target answer.
## Content
Extract the exact quoted string from the prompt and mentally complete the most frequent associated expression. For example, a quoted fragment like "put to" strongly activates the idiom "put to the [target]". This technique bypasses over-reliance on retrieved text by leveraging linguistic patterns inherent to the clue format.

# Success Memory Item 3
## Title
Align Candidate Terms with Domain Conventions
## Description
Cross-reference the linguistically derived candidate word against established terminology in the relevant field to confirm functional fit.
## Content
Once a candidate word emerges from idiom completion, validate it against standard usage within the implied domain. Confirm that the term functions correctly as both a technical label (e.g., for a specific type of event or object) and a natural fit for the idiomatic hint. Prioritize terms that demonstrate consistent dual usage across authoritative domain references.
