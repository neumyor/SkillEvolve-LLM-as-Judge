# Success Memory Item 1
## Title
Cross-Reference Context for Attribute Mapping
## Description
Systematically scan multiple retrieved documents to locate explicit mappings between a target entity and the requested attribute, ensuring the answer is grounded in consistent evidence across sources.
## Content
When a question asks for a specific property (e.g., trade name, synonym, or classification), extract direct statements linking the entity to that property from each document. Prioritize values that appear in multiple independent sources to confirm reliability before making a final selection.

# Success Memory Item 2
## Title
Resolve Ambiguity via Contextual Prominence
## Description
When the context contains multiple valid candidates for a single-answer question, select the option that is most frequently cited, explicitly labeled as primary/common, or best fits the question's singular framing.
## Content
Questions often imply a single expected answer even when several technically exist. Evaluate candidate options against contextual cues like frequency of mention, explicit qualifiers (e.g., "most commonly known"), and direct alignment with the prompt's wording to choose the most appropriate single response.

# Success Memory Item 3
## Title
Enforce Strict Output Formatting
## Description
Isolate the final answer string and place it exclusively within the required XML-style tags, omitting any reasoning, prefixes, or supplementary text to guarantee format compliance.
## Content
After determining the correct answer, strip away all explanatory text, alternative options, and conversational filler. Output only the precise answer string enclosed in the mandated tags to meet evaluation criteria and prevent parsing failures.
