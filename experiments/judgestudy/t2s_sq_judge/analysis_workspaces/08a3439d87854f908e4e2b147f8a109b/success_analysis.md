# Success Memory Item 1
## Title
Leverage Exact Statistical Anchors
## Description
Treat precise numerical values from the question as primary search keywords to rapidly isolate relevant context passages.
## Content
When a query contains specific quantitative data (e.g., rates, densities, counts, years), scan the retrieved documents for exact or near-exact matches first. These numeric anchors typically appear in summary tables, statistical reports, or lead sentences, allowing immediate narrowing of candidate sources before processing broader semantic cues.

# Success Memory Item 2
## Title
Corroborate with Secondary Qualifiers
## Description
Confirm a numeric match by checking for alignment with geographic, categorical, or superlative descriptors in the same passage or adjacent documents.
## Content
After locating a passage that matches a key statistic, verify that surrounding text supports additional question constraints such as region, political status, or ranking claims. Only commit to an entity when both the quantitative signal and qualitative descriptors point to the same subject, preventing false positives from similarly structured but geographically or categorically mismatched entries.

# Success Memory Item 3
## Title
Isolate and Format the Target Entity
## Description
Extract only the core subject name linked to the confirmed match and wrap it in the specified output tags without supplementary explanation.
## Content
Once the correct entity is identified, strip away contextual details, units, or supporting phrases. Return solely the proper noun or canonical name inside the required delimiters (e.g., `<answer>...</answer>`). This minimizes token noise, satisfies strict evaluation parsers, and maintains response efficiency.
