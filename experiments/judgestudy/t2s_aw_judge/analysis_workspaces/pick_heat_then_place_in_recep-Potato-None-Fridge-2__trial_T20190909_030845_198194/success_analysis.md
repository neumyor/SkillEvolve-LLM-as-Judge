# Success Memory Item 1
## Title
State Verification & Fallback Search Strategy
## Description
Prevent navigation loops and dead ends by verifying current holdings and systematically searching alternative high-probability locations when initial object retrieval fails or state becomes ambiguous.
## Content
Always execute `inventory` to confirm possession before proceeding. If the target object is missing or the environment state resets unexpectedly, do not assume it is gone; instead, navigate to common storage surfaces like countertops or open cabinets. Re-attempt acquisition only after confirming the object's presence in the new location.

# Success Memory Item 2
## Title
Explicit Appliance Heating Protocol
## Description
Rely on direct heating commands rather than implicit state changes, as microwaves require a specific interaction sequence to register temperature updates.
## Content
Place the object inside the appliance, close the door, then reopen it to retrieve the item. Crucially, use the explicit `heat <object> with <appliance>` command after retrieval to guarantee the temperature state changes. Do not skip this step or assume placement alone triggers heating.

# Success Memory Item 3
## Title
Target Receptacle State Management
## Description
Ensure the destination container is fully open and accessible immediately before executing the final placement action to avoid invalid moves.
## Content
Navigate directly to the target receptacle and verify its state. If closed, open it first. Only proceed with `move <object> to <receptacle>` when standing adjacent to the open container. This prevents placement failures caused by closed doors or incorrect spatial targeting.
