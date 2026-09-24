# Success Memory Item 1
## Title
Direct Extraction for Grammatical Identification
## Description
Extract the exact word fulfilling a requested grammatical role when the context explicitly confirms its usage in the target phrase.
## Content
For questions asking to identify a specific part of speech within a given phrase, locate the word that modifies the relevant verb or noun. Rely on contextual statements that explicitly classify the word in that exact construction. Return only the identified term inside the required tags, omitting all explanatory text to ensure precise matching.

# Success Memory Item 2
## Title
Context-Dependent Part-of-Speech Resolution
## Description
Resolve dual-role words by prioritizing their functional classification within the specific syntactic frame provided.
## Content
Many English words function as both adjectives and adverbs. When answering classification questions, ignore the word's standalone dictionary definition and instead analyze how it operates relative to the target verb or noun in the prompt. Use contextual examples that demonstrate the exact phrase to determine the correct grammatical label before extracting the answer.

# Success Memory Item 3
## Title
Strict Tag Enclosure for Single-Term Answers
## Description
Guarantee exact-match scoring by isolating the final answer within designated tags without supplementary commentary.
## Content
For direct identification tasks requiring a single word or short phrase, structure the final output to contain exclusively the target term wrapped in the specified XML-style tags. Avoid introductory phrases, reasoning summaries, or punctuation outside the tags, as automated evaluators typically perform strict string comparisons against the tagged content.
