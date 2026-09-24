# Success Memory Item 1
## Title
Structural Alignment for Direct Extraction
## Description
Match the syntactic structure of the question directly to context sentences to isolate the target entity.
## Content
When a prompt uses phrasing nearly identical to a source passage, locate the corresponding sentence and extract only the missing noun or proper name. This bypasses unnecessary inference and leverages explicit textual evidence.

# Success Memory Item 2
## Title
Immediate Constraint Application
## Description
Wrap the finalized answer in the required tags during the generation step to ensure strict compliance.
## Content
Upon identifying the correct span, apply the mandated output format (e.g., <answer>...</answer>) before producing any explanatory text. This guarantees that parsing systems receive a clean, structured response.

# Success Memory Item 3
## Title
Redundancy Leverage for Confidence
## Description
Use repeated factual statements across multiple documents as internal confirmation rather than treating them as conflicting data.
## Content
When retrieved context contains identical or highly similar statements about a single fact, prioritize the shared information. Recognizing redundancy streamlines decision-making and confirms the answer without requiring cross-document synthesis.
