# Failure Cause Item 1
## Title
Lexical Form Mismatch (Singular vs Plural)
## Description
The agent correctly identified the biological entity cultivated by leafcutter ants but selected the singular form "fungus" instead of the dataset's canonical plural form "Fungi".
## Content
The agent's reasoning explicitly considered both "fungus" and "fungi" but settled on "fungus" based on its own preference for the singular term found in some passages. The evaluation metric (EM/F1) penalized this lexical mismatch, resulting in a score of 0.0 despite the semantic correctness of the answer. The agent should have recognized that trivia datasets often expect the specific plural form "Fungi" when referring to the general category of organisms farmed by these ants.

# Failure Memory Item 1
## Title
Prioritize Canonical Dataset Lexicon Over Semantic Equivalence
## Description
When multiple synonymous forms exist in the context (e.g., "fungus" vs "Fungi"), prefer the exact lexical form used in standard reference answers or the most frequent canonical usage in the domain, rather than arbitrarily choosing one synonym.
## Content
In SearchQA-style tasks, exact string matching or high token overlap is required for scoring. Agents should avoid self-correcting to a semantically equivalent but lexically distinct variant unless the context strongly dictates one specific form. If unsure, defaulting to the plural or the most common scientific designation often aligns better with ground truth keys.

# Failure Memory Item 2
## Description
Trivial Quiz Questions Often Have Single-Word Canonical Answers
## Content
Questions formatted like fill-in-the-blank trivia ("Leaf cutter ants cut this, which they grow...") typically expect a single, concise noun. Agents should resist over-complicating the answer with phrases like "fungus gardens" or adding explanatory text, sticking strictly to the core entity name.

ACTION: TASK_COMPLETE
