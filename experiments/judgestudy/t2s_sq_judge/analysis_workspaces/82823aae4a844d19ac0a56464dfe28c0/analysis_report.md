# Failure Cause Item 1
## Title
Morphological Form Mismatch Between Agent Answer and Gold Answer
## Description
The agent correctly identified the term "meander" from the retrieved context, which explicitly defines it as "to follow a winding and turning course" and traces its etymology to the Maeander River in Phrygia. However, the gold answer is "Meandering" (a gerund/participle form), while the agent provided "meander" (the base verb). This is a span-boundary and lemma mismatch rather than a factual or reasoning error.
## Content
The context passages consistently use the base form "meander" when defining the term and explaining its origin. The agent faithfully extracted the exact word presented in the context. The scoring failure (EM: 0.0, F1: 0.0) stems from the gold answer using a different morphological variant ("Meandering") that does not appear verbatim in any retrieved passage. The judge confirmed that "meander" is the correct answer supported by the context, validating the agent's extraction decision.

# Failure Memory Item 1
## Title
Trust the Exact Lexical Form Present in Context
## Description
When extracting an answer span, prefer the exact word form (base verb, noun, gerund, etc.) as it appears in the supporting passage, rather than inferring or normalizing to a different grammatical variant.
## Content
Retrieved context often presents terms in their dictionary headword form (e.g., "meander") rather than in the specific grammatical form requested by the question (e.g., "Meandering"). Agents should extract the span exactly as written in the supporting text. If the question asks for a "term," the base dictionary form is typically the intended answer unless the context explicitly uses a different form.

# Failure Memory Item 2
## Title
Distinguish Scoring Failures from Reasoning Failures
## Description
A low EM/F1 score does not always indicate incorrect reasoning; it may reflect a gold-answer mismatch where the ground truth uses a different lexical variant than what the context supports.
## Content
When diagnosing failures, verify whether the agent's answer is factually supported by the retrieved context before attributing the failure to flawed reasoning. Use the judge tool to confirm contextual support independently of gold answers. If the context supports the agent's answer, the failure is likely a gold-answer annotation issue (span boundary, capitalization, or morphological form) rather than an agent-side error.

ACTION: TASK_COMPLETE
