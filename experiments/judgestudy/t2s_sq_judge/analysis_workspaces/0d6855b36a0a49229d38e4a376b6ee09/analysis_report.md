# Failure Cause Item 1
## Title
Over-specification of Answer Span Due to Full Name Preference
## Description
The agent correctly identified the entity (Brutus) but produced "Marcus Junius Brutus" instead of the shorter, more commonly referenced "Brutus" found in the gold answer and prominently used in the context passages. The context repeatedly refers to him simply as "Brutus" in the key sentences matching the question's phrasing (e.g., "Nevertheless, he joined Cassius in the plot against Caesar"). The agent's reasoning acknowledged both options ("Marcus Junius Brutus" or "Brutus") but arbitrarily chose the longer form without justification from the question's wording or context preference.
## Content
The question asks for the person who "was made a praetor of Rome & joined Cassius in a little plot." Multiple context passages use "Brutus" as the primary identifier in these exact clauses. For example: "[DOC] Brutus, in ancient Rome - Infoplease: '...in 44 B.C., urban praetor. Nevertheless, he joined Cassius in the plot against Caesar.'" The agent recognized this match but expanded the answer to "Marcus Junius Brutus," which, while factually correct, is not the span most directly supported by the context's phrasing. The minimal corrected answer consistent with the context is "Brutus."

# Failure Memory Item 1
## Title
Prefer Shortest Context-Supported Span for Entity Answers
## Description
When multiple valid name forms exist (e.g., full name vs. common name), prefer the shortest span that appears directly in the supporting context passages near the matching clues. This avoids over-specification and aligns with how SearchQA gold answers are typically formatted.
## Content
In this case, the context uses "Brutus" in the immediate vicinity of the matching predicates ("praetor in 44 B.C.", "joined Cassius in the plot"). The agent should have selected "Brutus" rather than expanding to "Marcus Junius Brutus," which requires inference beyond the immediate context span.

# Failure Memory Item 2
## Title
Avoid Arbitrary Choice Between Equally Valid Answer Forms
## Description
When the agent identifies multiple candidate answer spans that are equally valid, it should default to the most concise form that appears verbatim in the context near the matching evidence, rather than making an arbitrary choice between variants.
## Content
The agent explicitly noted both "Marcus Junius Brutus" and "Brutus" as acceptable but chose the former without contextual justification. A generalizable rule is: when in doubt between a short and long form, select the short form if it appears directly in the relevant context sentences.

ACTION: TASK_COMPLETE
