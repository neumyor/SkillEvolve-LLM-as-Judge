# Failure Cause Item 1
## Title
Definite Article Omission in Entity Answer Span

## Description
The agent correctly identified the target entity (University of Wisconsin-Superior) from the retrieved context but failed to include the definite article "the" when extracting the answer span, resulting in an exact-match failure despite semantic correctness.

## Content
The agent's reasoning correctly traced Arnold Schwarzenegger's graduation to the University of Wisconsin-Superior based on multiple context passages. However, when formulating the final answer, the agent output "University of Wisconsin-Superior" without the definite article. Several context passages use the phrasing "from the University of Wisconsin-Superior," suggesting the complete noun phrase includes "the." The agent committed to an answer but chose a slightly truncated span that omitted the leading determiner, causing an EM mismatch even though the F1 score (0.667) and sub-EM (1.0) indicated strong partial overlap with the expected answer.

# Failure Memory Item 1
## Title
Include Definite Articles When Extracting Named Entity Spans

## Description
When extracting answer spans from context, preserve leading definite articles ("the", "a") if they appear as part of the natural noun phrase in the source text, especially for institutional names.

## Content
Many institutional and proper noun phrases include definite articles as integral parts of their canonical form (e.g., "the University of Wisconsin-Superior" vs. "University of Wisconsin-Superior"). When the context uses the article as part of the full reference, include it in the extracted answer span to maximize exact-match compatibility. This is particularly important for university names, organizations, and other entities where the article may appear in both the question and the gold answer.

# Failure Memory Item 2
## Title
Prefer Context-Precise Answers Over Gold-Matching Heuristics

## Description
When the retrieved context provides a more specific or accurate answer than the gold label suggests, trust the context over assumptions about what the gold answer might be.

## Content
In this case, the gold answer "the University of Wisconsin" is less specific than the context-supported answer "the University of Wisconsin-Superior." The context consistently identifies the institution with its full name including the location qualifier. Agents should prioritize the precision and specificity supported by the retrieved evidence rather than attempting to guess a potentially abbreviated or imprecise gold label. This prevents unnecessary corrections that reduce answer quality.

ACTION: TASK_COMPLETE
