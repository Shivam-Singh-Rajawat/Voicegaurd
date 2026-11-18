# Recorded-audio joint validation protocol

This plan covers local microphone capture and supplied files. Track each as
a separate acquisition scope; decoding a saved microphone clip as a file
does not create a second independent trial. Telephone is deferred.

## Trial intake

Use one row per probe and claimed enrollment template. Record trial ID,
acquisition scope, partition, actual speaker ID (where known), claimed
speaker ID, probe session, enrollment session IDs, and recording condition
and device. Link enrollment and probe asset IDs with content hashes. Track
source recording lineage for replayed, synthesized, re-encoded, or clipped
assets. Record authorization and label provenance. Keep identifying details
and audio separate from shared metric exports.

Record speaker relationship (target, impostor, unknown), speech origin
(human, synthetic, unknown), and presentation (direct, replay, unknown)
as separate fields so that synthetic replay is representable. Label from
verified provenance, never from detector scores. A supplied file with
unknown recording history is not a verified direct or replay trial.

## Freeze and assess

1. Inventory eligible data before scoring. Split by speaker (actual and
   claimed), session and source lineage; check for duplicate content
   across calibration and held-out assessment. Enrollment and probe must
   use different sessions. Report missing labels and exclusions separately.
2. Run the pinned LA, PA and ECAPA paths on the same trials. Keep raw
   scores, missing evidence, abstention reasons, and model/config digests.
3. Agree on maximum genuine rejection, impostor acceptance, synthetic
   acceptance, replay acceptance and abstention for each supported scope
   before selecting a policy. Fit on calibration only. Freeze the policy
   and compare with the current heuristic on held-out data. Include
   independent continuous microphone sessions before claiming live behavior.
4. Report per-scope and per-condition trial counts, error rates among
   decisions, unconditional errors per eligible trial, coverage, and
   abstentions. Report sample uncertainty with speaker/session dependence
   accounted for, or mark estimates inconclusive when support is sparse.

Status: protocol ready for intake. No representative aligned trial set or
agreed limits yet. The demo keeps its current uncertain decision and the
frozen model assets and cutoffs remain in place.

## Existing data audit

PBS 46076 verified official ASVspoof 2019 development file coverage for
29,548 LA trials and 41,040 PA trials. LA supplies identity claims and
logical-access spoof labels. PA supplies identity claims and physical replay
labels in its own protocol. Neither protocol verifies all three label axes
for the same representative microphone or supplied-file acquisition.
Scoring all three models on either corpus cannot supply the missing labels.
Pooling the two protocols would confound attack type with corpus and
acquisition. Keep the saved scoped results as research baselines.

CN-Celeb1 provides identity trials and recording conditions. Its speaker
trial keys do not establish synthetic origin or physical replay. The
official assessment is reserved, and development scoring is complete.
Codecfake supplies synthetic speech evidence in its evaluated scope.
MUCS and IndicVoices response audits do not establish joint attack labels.
The verified Windows recording and file round trip provides one capture
path check. It does not provide independent calibration or assessment
cohorts. No eligible joint dataset is established by the saved evidence.

## Proposed limits for approval

These are provisional validation targets for the current demo scope, not
measured performance or approved operating limits. Apply them separately
to each acquisition scope before considering a joint policy for use.

| Metric | Proposed maximum | Denominator |
| --- | ---: | --- |
| Genuine target rejection | 10% | Eligible verified human direct target trials |
| Impostor acceptance | 1% | Eligible verified human direct impostor trials |
| Synthetic acceptance | 5% | Eligible verified synthetic trials |
| Replay acceptance | 5% | Eligible verified replay trials |
| Abstention | 10% | Eligible trials in each of the four groups |

Accept, reject and abstain are mutually exclusive. Report these rates over
all eligible trials, and publish error rates among decided trials as well.
A synthetic replay enters both applicable attack denominators. Report the
synthetic-replay intersection separately. Count operational abstentions
among eligible trials and disclose any intake exclusions with reasons.
An under-supported group is inconclusive. Report cluster-aware uncertainty
by speaker or session when support permits, and require the upper one-sided
95% confidence bound to meet the approved limit before declaring a pass.
Report each acquisition scope independently. The stricter impostor target
reflects the consequence of accepting the wrong identity. The abstention cap
prevents meeting error targets by declining most cases. Confirm or revise
these limits before fitting. Calibration also requires eligible aligned data.

## Collection workflow

1. Get permission from each participant for local recording and the intended
   evaluation. Assign pseudonymous speaker IDs. Reserve speaker groups for
   calibration and assessment before recording. Keep the participant key
   and audio in private storage.
2. Record one or more clean enrollment clips per speaker. In separate
   sessions, capture direct speech for probes and log the microphone,
   room and session ID. Match a probe to its own enrolled speaker for a
   genuine trial, or to another enrolled speaker within the same partition
   for an impostor trial. Keep each probe and its derived trials together.
3. Use authorized synthetic clips with documented generator and source
   lineage. Record replay trials by playing authorized clips through a
   loudspeaker and recapturing them with the microphone. Log the source,
   playback device and capture session. Keep all variants of a source
   within one partition. Leave unknown labels unknown and report exclusions.
4. For supplied files, record the original capture and presentation history.
   Run the file path on independently sourced material for its own
   assessment. A saved mic capture can verify file-path parity.
5. Copy the header below into a private CSV. Use one row per probe and
   claimed template. Use pipe separators for multiple enrollment IDs.
   Record provenance with each trial and keep raw evidence beside the
   manifest. Recordings of about five seconds exercise the existing demo.

```csv
trial_id,scope,partition,probe_path,probe_sha256,probe_session,source_lineage,actual_speaker,claimed_speaker,enrollment_paths,enrollment_sha256s,enrollment_sessions,relationship,origin,presentation,condition,capture_device,playback_device,generator,label_provenance,authorization_id
```

The user approved the provisional rates above for this validation plan.
Apply them when representative separated data are available. Approval of
the rates does not establish that any current policy meets them.

## Automated strict acceptance check

The reproducible helper `model_work/gate_acceptance.py` consumes a
private copy of the trial CSV above **augmented with**
`synthetic_score,replay_score,speaker_similarity` for every trial.
Use the exact provenance, partition and authorization columns shown
above; supply `calibration` and `assessment` as partition values,
`microphone` or `file` as separate scopes. Use only verified
`human|synthetic` origin, `direct|replay` presentation and
`target|impostor` speaker relationships.

Example using an existing fully scored and authorized manifest:

~~~powershell
py -3.14 model_work/gate_acceptance.py C:\private\aligned_trials.csv --report C:\private\gate_results.json
~~~

The helper fails closed on missing or inconsistent speaker claims,
enrollment/probe session duplication, re-used audio, cross-partition
speaker/source lineage overlap, and unscorable trials. It fits
threshold candidates on **calibration only**, assesses held-out
groups once and uses a conservative one-sided 95% speaker-cluster
error upper bound for the previously approved limits. A tiny
dataset with zero observed errors is **not** a pass.

For independent model acceptance, separately verify genuine source
annotations, recording-session independence, source lineage,
checkpoint digests, acquisition representativeness and limits
before promoting any calculated result to a deployed security policy.
This tool does not create labels, invent authorizations or discover
recording sessions. EchoFake's native dev rows lack the required
speaker/enrollment provenance and produce a blocked gate report.
