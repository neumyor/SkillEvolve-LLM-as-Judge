# Failure Cause Item 1
## Title
Span Selection Error on "these" Reference Questions
## Description
The agent extracted the organization name instead of the business type when the question asked for "these Chinese businesses," misinterpreting the referent of "these."
## Content
The question uses "these" to signal that the answer should be a category/type of business, not a proper noun organization name. The agent correctly identified the relevant passages about the Chinese Hand Laundry Alliance but failed to parse the question's grammatical framing: "the alliance of **these** Chinese businesses" asks what kind of businesses were allied, not what the alliance was called. The agent committed to the most prominent entity in the retrieved context (the organization name) rather than the business type ("laundries") that the question structure actually requested. This is a span-selection error driven by entity salience overriding question semantics.

# Failure Memory Item 1
## Title
Parse Question Grammar Before Selecting Answer Spans
## Description
When a question contains demonstrative references like "these [noun]," the answer is typically the category or type being referenced, not a proper name that appears nearby in the text.
## Content
Questions often use pronouns and demonstratives ("these," "those," "this") to point to a specific semantic role. Agents should first determine what grammatical role the question is asking for (type vs. name vs. date vs. location) before scanning for candidate spans. In this case, "these Chinese businesses" unambiguously requests a business category, making "laundries" the correct span even though the organization name "Chinese Hand Laundry Alliance" is more prominently featured in the same passages.

# Failure Memory Item 2
## Title
Prioritize Question Semantics Over Passage Entity Salience
## Description
Do not default to extracting the most prominent or longest-named entity from a passage; always verify that the extracted span matches the specific semantic role requested by the question.
## Content
Retrieved passages often contain multiple entities, and the most visible one (e.g., a proper noun with capital letters) may not be the answer. Agents should explicitly map each question phrase to its expected answer type before selecting a span. A generalizable heuristic: if the question asks "what kind of X" or "these Xs," the answer is a common noun describing the category, not a proper name. This prevents the common failure mode of answering with a related but incorrect entity simply because it dominates the context.

ACTION: TASK_COMPLETE
