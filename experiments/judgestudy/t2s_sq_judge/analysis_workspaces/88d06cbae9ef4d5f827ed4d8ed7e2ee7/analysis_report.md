# Failure Cause Item 1
## Title
Over-specification of Answer Span
## Description
The agent selected "Speech balloon" instead of the more precise single-word term "balloon" (or "a balloon") that the context and trivia question expect. The agent recognized multiple valid terms ("speech balloon", "speech bubble", "word balloon") but failed to identify that the core term defined in the Comicraft glossary is simply "balloon".
## Content
The agent's reasoning showed it considered "Speech balloon", "Speech bubble", and "Word balloon" as candidates. It settled on "Speech balloon" because it appeared in a document title and was explicitly mentioned. However, the Comicraft Glossary passage defines "BALLOON" as the "circular shape used to contain speech," which is the direct answer to "Term for the circle...". The agent committed to a multi-word phrase when the context supports the single-word head term. This is a span-boundary/precision error where the agent chose a descriptive compound over the specific terminology defined in the source.

# Failure Memory Item 1
## Title
Prefer Head Terms Over Descriptive Compounds
## Description
When a glossary or definition entry defines a single word (e.g., "BALLOON - circular shape used to contain speech"), prefer that head term as the answer rather than a longer descriptive phrase (e.g., "speech balloon") that may appear elsewhere in the context.
## Content
In trivia and terminology questions, the expected answer is often the specific term being defined. If a passage says "BALLOON - circular shape used to contain speech," the answer to "what is the term for the circle..." is "balloon," not "speech balloon." Always check if the context provides a direct definition of a single word that matches the question's phrasing.

# Failure Memory Item 2
## Title
Adjudicate Between Synonyms by Definition Precision
## Description
When multiple synonymous terms exist in the context (e.g., "speech balloon" vs. "balloon"), prioritize the term that is directly defined or most precisely matches the question's wording.
## Content
The agent had access to both "Speech balloon" (as a document title and concept) and "Balloon" (as a defined term in the Comicraft glossary). The question asks for the "term for the circle," and the glossary explicitly defines "BALLOON" as the "circular shape used to contain speech." The agent should have recognized this as the most precise match and selected "balloon" over the longer variant.

ACTION: TASK_COMPLETE
