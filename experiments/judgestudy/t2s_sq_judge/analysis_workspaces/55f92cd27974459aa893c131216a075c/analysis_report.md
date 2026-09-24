# Failure Cause Item 1
## Title
Middle Initial Inclusion Span-Boundary Error
## Description
The agent correctly identified the president as Lyndon B. Johnson based on the retrieved context, but the gold answer is "Lyndon Johnson" without the middle initial. This is a span-boundary/variant mismatch rather than a factual error.
## Content
The agent's output "Lyndon B. Johnson" received an F1 of 0.8 and EM of 0.0, indicating a near-miss. The context contains references to both "Lyndon B. Johnson" and "Lyndon Johnson" / "LBJ". The agent chose the fuller form with the middle initial "B.", while the benchmark's expected answer omits it. The fix was to drop the middle initial to produce "Lyndon Johnson", which the judge confirmed is fully supported by the context passages that refer to him as "Lyndon Johnson" and "LBJ".

# Failure Memory Item 1
## Title
Prefer Shortest Unambiguous Entity Span
## Description
When extracting entity answers from context, prefer the shortest form that uniquely identifies the entity rather than adding qualifiers like middle initials or full titles unless explicitly required.
## Content
Many QA benchmarks expect the minimal canonical span (e.g., "Lyndon Johnson" vs "Lyndon B. Johnson"). If the context supports multiple valid forms, default to the shortest unambiguous variant. This avoids over-specification that causes exact-match failures while preserving semantic correctness.

# Failure Memory Item 2
## Title
Adjudicate Name Variants by Context Frequency and Directness
## Description
When context contains multiple name variants for the same entity, check which form appears in the most direct supporting passage and align with that form for extraction.
## Content
In this case, several passages use "Lyndon Johnson" or "LBJ" directly alongside the quote, while others use "Lyndon B. Johnson". The agent should have noted that the shorter form appears in passages that more directly link the speaker to the quote (e.g., "the president stated: 'The Great Society rests on abundance and liberty for all'") and preferred that span. This generalizes to any entity extraction task where naming conventions vary across sources.

ACTION: TASK_COMPLETE
