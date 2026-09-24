# Success Memory Item 1
## Title
Direct Landmark-to-Region Mapping
## Description
Extract the target jurisdiction by locating explicit contextual statements that directly pair the queried landmark with its governing administrative division.
## Content
When a prompt centers on a specific geographic feature or peak, prioritize retrieved passages containing unambiguous declarative links (e.g., "[Feature] is the highest point in [State]"). Relying on these direct factual assertions eliminates guesswork and rapidly isolates the correct entity.

# Success Memory Item 2
## Title
Semantic Nickname Resolution
## Description
Map colloquial descriptors, cultural aliases, or thematic hints in the query to the formal geographic names found within the context.
## Content
Questions frequently substitute official names with recognizable monikers or regional characteristics (e.g., "peachy state"). Identify the formal entity extracted from the text, then align it with the prompt's descriptive phrasing to confirm semantic equivalence and finalize the answer.

# Success Memory Item 3
## Title
Syntax-First Output Construction
## Description
Isolate the resolved answer token and immediately apply the required structural wrapper before generating the final response.
## Content
Strict formatting rules require precise tag placement. Determine the exact answer string first, then wrap it in the mandated delimiters (e.g., `<answer>...</answer>`). Constructing the output structure around the isolated token prevents formatting drift and guarantees parseable delivery.
