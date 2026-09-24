# Failure Cause Item 1
## Title
Arbitrary choice between synonymous answer variants without preferring the best lexical match to the question
## Description
The agent identified two valid candidate answers — "filo" and "phyllo" — both of which mean "leaf" in Greek and are used to make baklava. Rather than selecting the variant that most closely aligns with the question's specific phrasing, it arbitrarily picked "Filo." The question asks about a pastry "whose name is Greek for 'leaf'," and the passage stating "The name 'phyllo' comes from Greek language, meaning 'leaf.'" provides a near-exact lexical match. The agent failed to adjudicate between synonymous options by weighing which one the question's wording most directly targets.
## Content
The retrieved context contains multiple passages referencing both "filo" and "phyllo" as interchangeable names for the same paper-thin pastry. The agent correctly recognized this equivalence but did not use the question's framing ("whose name is Greek for 'leaf'") as a tiebreaker. One passage explicitly says "The name 'phyllo' comes from Greek language, meaning 'leaf,'" which mirrors the question's structure more precisely than the passage saying "Filo (or phyllo) (Greek: 'leaf')." The agent should have preferred the term whose contextual presentation most directly supports the specific angle of the question.

# Failure Memory Item 1
## Title
Prefer the answer variant whose contextual presentation most closely matches the question's wording
## Description
When multiple synonymous or variant terms appear in the retrieved context, do not pick arbitrarily. Instead, evaluate which variant the question's specific phrasing most directly targets — for example, if the question references a word's etymology, prefer the passage that explicitly discusses that etymology using the variant in question.
## Content
In this case, the question asked about a pastry "whose name is Greek for 'leaf'." The passage explicitly stating "The name 'phyllo' comes from Greek language, meaning 'leaf'" is a stronger match than the passage listing "Filo (or phyllo)" together. Generalizing: when faced with synonymous candidates, scan for the passage whose wording most closely mirrors the question's key phrases and select the term presented there.

# Failure Memory Item 2
## Title
Output only the single answer span, not alternatives or parenthetical notes
## Description
The task requires a concise final answer inside `<answer>` tags. Including alternatives like "Filo (or Phyllo)" or hedging language violates the output contract and can confuse downstream evaluation. Always commit to one definitive span.
## Content
The agent's reasoning acknowledged both "filo" and "phyllo" as acceptable but still needed to produce a single output. In general, after identifying valid candidates, the agent must make a firm selection and output only that selected span — never alternatives, disclaimers, or combined forms — to ensure clean evaluation.

ACTION: TASK_COMPLETE
