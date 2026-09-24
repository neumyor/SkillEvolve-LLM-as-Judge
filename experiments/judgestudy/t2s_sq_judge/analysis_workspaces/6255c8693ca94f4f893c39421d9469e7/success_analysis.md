# Success Memory Item 1
## Title
Map Unique Cultural or Award Terms to Primary Jurisdictions
## Description
When a question uses a specific award, title, or cultural marker to identify a country or organization, isolate the distinctive term and directly extract its primary national or organizational association from the context.
## Content
1. Identify the unique keyword or phrase in the prompt (e.g., award name, institutional title).
2. Scan retrieved documents for explicit statements linking that term to a country, region, or organization.
3. Extract only the target entity name, ignoring secondary details or historical timelines unless specifically requested.

# Success Memory Item 2
## Title
Align Extracted Answers with Explicit Context Definitions
## Description
Ensure the final answer directly corresponds to unambiguous statements in the provided documents, prioritizing primary definitions over peripheral mentions or related concepts.
## Content
1. Locate sentences that pair the query keyword with candidate entities.
2. Confirm the relationship matches the question's premise by checking for direct attribution phrases (e.g., "highest civilian award of...", "instituted by...").
3. Select the exact term used in the context to maintain precision and avoid synonym substitution.

# Success Memory Item 3
## Title
Enforce Strict Answer Tagging Without Extraneous Text
## Description
Structure the final response to contain only the required answer within the specified tags, stripping away reasoning steps, greetings, or explanatory text to meet evaluation criteria.
## Content
1. Draft the raw answer string based on the extracted entity.
2. Wrap exclusively in the required format tags (e.g., `<answer>...</answer>`).
3. Verify tag placement, capitalization, and spelling match the prompt exactly before submission.
