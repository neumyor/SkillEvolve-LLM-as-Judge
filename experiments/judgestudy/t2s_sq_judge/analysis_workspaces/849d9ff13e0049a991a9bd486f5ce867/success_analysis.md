# Success Memory Item 1
## Title
Definitional Phrase Matching
## Description
Identify target terms by aligning descriptive prompts with explicit dictionary-style definitions in the context.
## Content
When a question describes a word's meaning, usage, or characteristic sound, scan retrieved documents for direct definitional statements that mirror the prompt's phrasing. Extract the headword associated with the matching definition.

# Success Memory Item 2
## Title
Prompt-Context Alignment
## Description
Confirm the candidate term satisfies every specific condition outlined in the question.
## Content
After identifying a potential match, systematically compare it against all details in the prompt (e.g., physical properties, contextual modifiers, or usage notes). Proceed only when the context explicitly supports each element of the query.

# Success Memory Item 3
## Title
Strict Tag Encapsulation
## Description
Isolate the final answer within the designated XML-style tags, excluding any surrounding reasoning or conversational text.
## Content
Once the correct term is confirmed, output only the raw answer string wrapped in the required `<answer>...</answer>` tags. Ensure no extra whitespace, explanations, or markdown interferes with the parsing requirements.
