# Success Memory Item 1
## Title
Targeted Attribute Extraction
## Description
Isolate the specific missing variable requested in the prompt and scan retrieved documents exclusively for that attribute paired with the target entity.
## Content
Parse the question to identify the exact field needed (e.g., flavor, date, location). Filter retrieved snippets to locate direct statements linking the target term to that specific attribute, ignoring tangential recipe steps or unrelated variations.

# Success Memory Item 2
## Title
Cross-Document Consensus Building
## Description
Aggregate explicit definitions across multiple independent sources to identify the dominant pattern, treating repeated mentions as high-confidence signals.
## Content
When faced with slight variations in retrieved context, count and compare how frequently each variant is stated. Prioritize the attribute consistently cited across the majority of documents, using outlier mentions only if they represent a recognized alternative rather than an error.

# Success Memory Item 3
## Title
Minimalist Value Mapping
## Description
Convert the extracted attribute directly into the final output without explanatory text, ensuring strict compliance with formatting requirements.
## Content
Once the correct value is identified, strip all surrounding context, measurements, or preparatory instructions. Return only the precise noun or phrase that completes the question's premise, enclosed strictly within the designated response tags.
