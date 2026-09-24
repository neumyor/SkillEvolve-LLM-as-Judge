# Success Memory Item 1
## Title
Enforce Categorical Constraints During Candidate Selection
## Description
Use explicit category descriptors in the prompt to filter out semantically mismatched options from the retrieved context, even when multiple related entities are present.
## Content
When the context lists several potential answers (e.g., coffee, bananas, sugar), cross-reference them against explicit categorical terms in the question (e.g., "fruit crop") to isolate the correct match before evaluating supporting details or statistics.

# Success Memory Item 2
## Title
Resolve Statistical Ambiguity via Consistent Contextual Signaling
## Description
When retrieved snippets contain outdated, partial, or contradictory numerical data, prioritize the entity most consistently highlighted as a primary economic driver for the target subject.
## Content
If exact percentages or rankings do not align perfectly across sources, rely on repeated contextual emphasis (e.g., "principal export crops," "leading source of income") combined with domain familiarity to select the most plausible answer rather than discarding it due to minor data mismatches.

# Success Memory Item 3
## Title
Isolate Final Answer in Designated Output Tags
## Description
Extract only the definitive answer string and place it within the required formatting tags, completely separating it from internal reasoning or supplementary text.
## Content
Maintain strict boundary between deliberation steps and the final response to ensure automated parsers can reliably capture the output. Omit qualifiers, explanations, or conversational filler inside the designated tags.
