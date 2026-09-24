# Success Memory Item 1
## Title
Handle Declarative or Clue-Style Query Phrasing
## Description
Recognize when prompts are structured as trivia clues, fill-in-the-blanks, or partial statements rather than direct questions, and map them to explicit attribute extraction.
## Content
When a query uses declarative framing (e.g., "It's the traditional color of..."), treat it as a request for the missing subject or descriptor. Ignore conversational wrappers and directly locate the specific noun or adjective that satisfies the implied blank. Extract only that core term to align with standard trivia or quiz evaluation patterns.

# Success Memory Item 2
## Title
Validate via Multi-Snippet Consensus
## Description
Confirm factual accuracy by checking for consistent mentions across multiple retrieved passages before committing to an answer.
## Content
Avoid over-relying on a single document. Scan all provided snippets for overlapping references to the target fact. When independent sources consistently point to the same value, elevate it as the definitive answer. This mitigates noise from tangential details, outdated data, or operator-specific variations in the context pool.

# Success Memory Item 3
## Title
Strip Modifiers for Exact-Match Optimization
## Description
Distill the extracted fact to its simplest, most direct form to maximize compatibility with automated exact-match and fuzzy-score evaluation.
## Content
After identifying the correct attribute, remove descriptive qualifiers, full sentences, or contextual explanations (e.g., output "Red" instead of "Bright red" or "The buses are traditionally red"). Wrap only the distilled term in the required tags. This preserves precision for string-matching metrics while maintaining semantic correctness.
