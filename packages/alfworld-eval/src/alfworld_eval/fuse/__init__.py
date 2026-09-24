"""FUSE skill-evolution method adapted to the ALFWorld TextWorld harness.

Ports the SkillEvolveCPM FUSE flow (failed public trajectory -> diagnosis ->
candidate skill edit -> independent formal validation -> adopt or discard)
onto this repository's unified evaluation stack. The heavy TB2 runtime
(Harbor / Docker / E2B / native OpenClaw) is replaced by local OpenAI-compatible
tool-loop sessions, mirroring the trust boundaries of the original:

* episode reward signals (per-step ``won``/``done``) are scrubbed from the
  public trajectories an authoring session may read; the outcome lives only
  in the manifest;
* formal validation always re-executes real episodes through the ordinary
  evaluation harness with the candidate skill injected;
* a candidate is only staged when it passes static checks, the train-member
  acceptance gate (no regression, required gains), and never silently.
"""
