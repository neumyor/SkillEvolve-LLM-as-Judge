# Failure Cause Item 1
## Title
Span Selection Error: Including Disjunctive Qualifiers Instead of the Primary Entity
## Description
The agent correctly identified that an Anglican parish priest is called a "vicar" or "rector" based on the context. However, it selected the full phrase "vicar or rector" as the answer span instead of isolating the single canonical term "Vicar". In SearchQA-style questions, when multiple synonyms are provided (e.g., "usually called a vicar or rector"), the gold answer typically corresponds to one of the specific terms rather than the disjunctive phrase itself. The agent's reasoning explicitly considered "vicar" and "rector" separately but settled on the combined phrase due to ambiguity about which was preferred, leading to a sub-EM failure despite semantic correctness.
## Content
The agent saw passages stating "Each parish is overseen by a parish priest (usually called a vicar or rector)" and "A vicar is the priest in charge of a parish...". It reasoned that since both terms were present, it should include both. This is a common error where the model treats the explanatory text literally as the answer span rather than extracting the core entity. The correction to "Vicar" aligns with the context's definition ("A vicar is the priest in charge of a parish") and the gold answer.

# Failure Memory Item 1
## Title
Prefer Single Canonical Terms Over Disjunctive Phrases in Answer Spans
## Description
When the context provides multiple synonyms for an entity (e.g., "called X or Y"), the correct answer span is often just one of the terms (X or Y), not the conjunction "X or Y". Models should look for the most direct definitional match or the term that stands alone as the primary identifier.
## Content
In this case, "vicar" is defined directly as "the priest in charge of a parish". "Rector" is also valid, but "Vicar" is the gold standard. Selecting "vicar or rector" introduces unnecessary words that break exact match metrics. When faced with "usually called A or B", try selecting A first, especially if A appears in a standalone definition sentence.

# Failure Memory Item 2
## Title
Disambiguate Between Explanatory Text and Target Answer Span
## Description
Context sentences often contain parenthetical explanations or lists of alternatives (e.g., "(usually called a vicar or rector)"). The model must distinguish between the *explanation* and the *entity* being asked for. The question "An Anglican parish priest" asks for the title/identity, not the full descriptive clause.
## Content
The agent got stuck in the explanation text "usually called a vicar or rector" rather than extracting the noun phrase "vicar" or "rector". Generalizable lesson: When the question is a noun phrase fragment asking for a definition or title, extract the specific noun/title, not the surrounding descriptive modifiers or disjunctions.

ACTION: TASK_COMPLETE
