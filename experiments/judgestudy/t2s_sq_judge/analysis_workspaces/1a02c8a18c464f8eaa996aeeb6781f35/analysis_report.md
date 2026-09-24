# Failure Cause Item 1
## Title
Incorrect Span Selection for Entity-Type Factoid Questions
## Description
The agent correctly identified the relevant passage stating Tran Duc Luong was "president of Vietnam from 1997 to 2006," but it committed to the entire descriptive phrase "President of Vietnam from 1997 to 2006" as the answer. The question "President Tran Duc Luong" is a factoid query expecting the core entity associated with the subject (the country he presided over). The agent failed to isolate the specific entity "Vietnam" from the surrounding titular and chronological context.
## Content
In SearchQA-style tasks, short queries involving a person's name and title often target a specific attribute (e.g., country, birth place, party). The agent must distinguish between providing a summary description and extracting the precise answer span. Here, the presence of dates and titles in the source text led to an overly broad extraction. The correct behavior is to recognize that "Vietnam" is the distinct entity answering the implicit "Which country?" question, stripping away the role and tenure details.

# Failure Memory Item 1
## Title
Prioritize Minimal Entity Spans Over Descriptive Phrases
## Description
When the expected answer is an entity (person, location, organization), the output should contain only that entity name, not the sentence or phrase containing it.
## Content
Agents should analyze the question to determine the expected answer type. If the question asks for a person's affiliation or role-holder identity, and the context says "X was Y of Z from A to B," the answer is typically "Z" (the entity), not "Y of Z from A to B." Always trim titles, dates, and verbs unless they are integral parts of the proper noun itself.

# Failure Memory Item 2
## Title
Infer Target Attribute from Question Structure
## Description
Short, noun-phrase-only questions (e.g., "President Tran Duc Luong") often imply a specific missing attribute, commonly the country or organization associated with the role.
## Content
Do not treat such queries as requests for a biography. Instead, look for the most salient entity link in the top-ranked passages. If the gold answer is a location, ensure the extraction focuses on the location entity. Avoid defaulting to the first full clause encountered; instead, parse the semantic role of the question to select the matching span type.

ACTION: TASK_COMPLETE
