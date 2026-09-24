# Failure Cause Item 1
## Title
Generic Answer Selection Over Specific Entity Mention
## Description
The agent selected the generic term "Pelican" instead of the more specific "Brown pelican" despite multiple passages in the retrieved context explicitly identifying the Brown Pelican as Louisiana's official state bird depicted on the seal.
## Content
The agent's reasoning acknowledged both "pelican" and "Brown Pelican" as valid options but arbitrarily chose "Pelican" stating it was "sufficient." Several passages ([DOC] Louisiana State Seal for kids, [DOC] How did Louisiana get its nickname as 'The Pelican State'?, [DOC] Pelicans - water birds) explicitly name the "Brown Pelican" as the official state bird. The agent failed to prioritize the more precise taxonomic name when the context supported it, resulting in a near-miss where the answer overlaps the correct entity but lacks the required specificity.

# Failure Memory Item 1
## Title
Prioritize Specific Entity Names Over Generic Categories
## Description
When retrieved context provides both a generic category and a specific entity name (e.g., "pelican" vs. "Brown pelican"), the model should select the more specific term if it is explicitly tied to the question's subject.
## Content
State symbol trivia questions often expect the precise common name or species designation rather than the broader family or genus. If the context explicitly identifies a specific variant (e.g., "Brown Pelican is the Official State Bird"), use that exact phrasing. Defaulting to the generic term when a specific one is available leads to near-miss failures that miss exact match criteria.

# Failure Memory Item 2
## Description
When evaluating candidate answers from context, compare all mentions of the target entity and prefer the most granular designation that appears in passages directly answering the question.
## Content
Do not settle on the first or most frequent mention if a later passage provides a more precise identifier. Scan all relevant documents for explicit naming conventions (e.g., "official state bird," "depicted on the seal") and extract the full specific name rather than truncating to a common noun. This ensures the answer span matches the expected granularity for factual QA tasks.

# Failure Memory Item 3
## Title
Verify Granularity Against Contextual Evidence Before Finalizing
## Description
Before committing to an answer, check whether the context supports a more specific formulation than the initially considered option.
## Content
After identifying a candidate answer, perform a final scan of the context to see if any passage uses a more precise term for the same entity. If so, adopt that term. This prevents premature convergence on generic answers when the source material contains the exact phrasing needed for full credit.

ACTION: TASK_COMPLETE
