# November 17, 2026 — Ungated dataset options for Voicegaurd V1

## Decision

**SITW is held.** The screenshot supplied on November 17 still shows
`confit/sitw-full` pending on Hugging Face. Do not resume access polling
unless the user reports approval.

**Use EchoFake first for a bounded attack-response and joint-evidence intake
audit.** It is an openly listed Hugging Face dataset, not an official
cross-session speaker-verification protocol. The published repository includes
four splits and 75,490 files (~3.26 GB), with fields `utt_id`, `path`,
`label`, `source`, `source_speaker_id`, `replay_details`, and
`synthesis_details`:
https://huggingface.co/datasets/EchoFake/EchoFake .
The ICASSP 2026 paper reports bonafide, TTS and physical replay scenarios:
https://arxiv.org/abs/2510.19414 .

**ReplayDF is second priority for independent physical replay/AI-response
assessment**, if EchoFake's protocol or acquisition conditions are insufficient.
It includes rerecorded genuine and TTS speech through 109 loudspeaker–microphone
combinations; around 23.9 GB and under a non-commercial Creative Commons license:
https://huggingface.co/datasets/mueller91/ReplayDF .

**The best conceptual single-source dataset is voicePA** because it includes
44 identities across four sessions, genuine, replay, speech synthesis and voice
conversion, with participant-disjoint train/dev/eval. It cannot be assumed
available today: its ~204 GB distribution requires a signed institutional EULA,
a permanently employed signatory and a qualifying institutional address:
https://www.idiap.ch/en/dataset/voicepa
https://zenodo.org/records/4580204 .

**ASVspoof 5 is a complementary SASV reference, not a replay replacement.**
Its official Track 2 has target/nontarget/spoof trials and enrollment audio,
but the attack categories do not establish physical loudspeaker replay:
https://huggingface.co/datasets/jungjee/asvspoof5
https://www.asvspoof.org/ .

## Why neither remaining model gate can yet be marked passed

The current research status remains **7/9**, not 9/9.
The two open gates are:

1. **Realistic unseen-speaker robustness:** requires actual speaker IDs,
   independent enrollment/probe recording sessions, separate speaker cohorts,
   held-out assessment, frozen cutoff or calibration-only candidates, and
   FAR/FRR/EER/AUROC/coverage/abstention with uncertainty. A field called
   `source_speaker_id` is not evidence of capture-session separation.
2. **Calibrated joint risk:** needs aligned, provenance-verified labels for
   claimed and actual speaker, origin (human/synthetic), presentation
   (direct/replay) *on the same audio trial*, with calibration and speaker/
   source-disjoint assessment, including synthesized/replayed intersections.

The previously approved provisional limits per acquisition scope are at
most 10% genuine target rejection, 1% impostor acceptance, 5% synthetic
acceptance, 5% replay acceptance and 10% abstention. Check the one-sided
95% speaker/session-aware upper confidence bounds before claiming a pass.
The existing CoSG failure at the frozen LA cutoff and CN-Celeb/HI-MIA
speaker rejection rates are not fixed by downloading a new dataset.
Do not tune to a held-out benchmark. See
`RECORDED_AUDIO_JOINT_PROTOCOL.md` and `MODEL_VALIDATION.md`.

## Bounded implementation order (no new training authorized solely by this note)

1. **Inspect metadata before downloading full audio.** Record exact dataset
   revision, data terms, available labels, source lineage, speaker counts,
   per-speaker bona fide counts, session-ID existence, acquisition conditions,
   full-window eligibility at 4.0375 seconds, and whether identical source
   clips or same-speaker recordings cross split boundaries. Do not infer
   room/session from a device identifier.
2. **Build an explicit trial manifest.** Map each eligible record into
   `trial_id, scope, partition, probe_path, probe_sha256, probe_session,
   source_lineage, actual_speaker, claimed_speaker, enrollment_paths,
   enrollment_sha256s, enrollment_sessions, relationship, origin,
   presentation, condition, capture_device, playback_device, generator,
   label_provenance, authorization_id`. Leave unverifiable values UNKNOWN,
   not invented. Do not create speaker matches without independent authorized
   enrollment recordings and verified actual identities.
3. **Stage only the necessary dev audio in private workspace**, respecting
   licenses, HPC login-network restrictions, storage quotas, and the
   project write lock. Hash and retain dataset revision. Use a fresh bounded
   CPU PBS audit before scheduling justified GPU scoring. Do not duplicate
   finished prior analyses.
4. **Run frozen LA, PA, and ECAPA on identical eligible windows** and record
   scores, missing evidence, error/coverage counts and checkpoint digests.
   Treat arbitrary file and microphone inputs as different scopes. Keep
   audio <4.0375 s as abstention; never repeat-pad to inflate coverage.
5. **Calibrate only if verified aligned calibration trials exist.** Freeze
   thresholds before a disjoint held-out set, and report confidence bounds.
   Otherwise deliver a descriptive attack-response report, not a joint
   security pass.
6. **For the cross-session speaker gate**, if EchoFake lacks explicit
   enrollment/probe session provenance, find a separate permissioned
   cross-session cohort or collect consented recordings from different days,
   with actual identities and speaker-disjoint calibration/assessment.
   Do not reuse J-SpAW/HI-MIA or CN-Celeb evaluation for threshold selection.

## Execution constraints

As of this review, no audio was downloaded, no new PBS task was submitted
and no fresh detector evaluation has been run. The remote Windows Desktop
Commander device was offline at inspection. Existing test results and
frozen checkpoint provenance remain unchanged. Version 1 can continue as
an offline score-only microphone/file prototype while these research
gates stay open.

This note records source selection and scientific acceptance requirements,
not a claim that either gate passed or that the full demo is deployment-ready.
