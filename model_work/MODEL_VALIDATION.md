# Voicegaurd model validation record

**Research handoff ready for review. Model validation is 7 of 9 gates complete.** Each result below applies to the protocol and input conditions listed. Real-channel speaker robustness and representative joint-risk calibration remain blocked on the inputs documented below.

| Component | Verified evidence | Remaining decision |
| --- | --- | --- |
| Synthetic speech | Standalone WavLM: 1.2124% EER on 71,237 independent LA recordings in the preserved benchmark. ASVspoof5 development log loss 0.334 to 0.186 after temperature scaling on a separate calibration subset. | LA calibration target of 1% false positives transferred as 3.1% on selection. Do not treat temperature scaling as fixing this threshold shift or apply the older fusion threshold to standalone WavLM. |
| Replay | Original Attention: 9.2659% EER on the previously run independent PA evaluation. Fixed three-model mean: 6.68% EER vs 7.24% for Attention in matched speaker-grouped development folds. | Preserve Attention as the independent benchmark baseline. The fusion improvement needs separate validation and inference-cost assessment before promotion. |
| Speaker verification | ECAPA development assessment: 0.89% EER over 2,849 target and impostor trials. Official LA held-out subset (46111): 48 enrolled speakers, 1,152 scored trials, 0.868% EER and 0.99875 AUROC. At the frozen development cutoff, FAR was 2/576 (0.347%) and FRR was 14/576 (2.431%). | Held-out speakers were disjoint from the development protocol. ECAPA pretraining identity overlap, actual telephone audio, real noise and spoof performance are outside this held-out result. |
| Combined speaker/synthetic rule | Accepted 0/300 sampled LA development spoofs vs 92/300 with speaker verification alone. Added one genuine-match rejection, 27/756 vs 26/756, at unchanged thresholds. | No deployment security guarantee. Keep evaluation operating points frozen; evaluate on a new authorized challenge before making stronger claims. |
| Hindi-English response | 300 windows from 100 MUCS tutorial files. Synthetic score median 0.000000558; replay score median 0.998. | No replay ground truth. High replay scores indicate an unresolved recording-domain response shift, not a measured false-positive rate. Do not use replay evidence as a general-purpose veto. |
| IndicVoices response | At frozen thresholds, file-weighted replay exceedance was 73% on IndicVoices and 90.67% on MUCS. Results were similar after excluding windows below RMS 0.01. | Replay provenance is unknown for both corpora. These figures describe score distributions. |
| Codecfake | On 1,372 scored CoSG files, EER was 21.72% and AUROC was 0.8779. The frozen LA threshold flagged 121/736 spoof files and 3/636 bona fide files. The detector abstained on 425 more files. Stored hashes found zero exact-byte matches with 207,737 checked training files. | Low detection at the frozen threshold and incomplete coverage are open. Evaluate changes on separate development data. Transformed and near-duplicate overlap is still unverified. |
| Noise and bandwidth | Speaker false nonmatches rose from 5/100 in clean audio to 13/100 at 20 dB and 23/100 at 10 dB. Both 8 and 16 kHz PCM passed ingestion and short-audio checks. The paired 8 kHz PA sample had three genuine flags versus one at 16 kHz. | Synthetic noise and simulated bandwidth are controlled development tests. Actual telephone codecs, real noise, and additional recording conditions need separate evidence. |
| Scoped joint risk | LA fusion and the existing rule agreed on all 150 scored assessment trials, with 350 of 500 trials abstaining. PA scored 417 of 828 assessment trials. The experimental fusion denied 236/276 spoofs and 5/50 genuine matches versus 208/276 and 2/50 with the baseline rule. | LA showed no decision gain at the compared cutoffs. PA gained spoof rejection at the cost of more genuine rejections and one accepted impostor. Both scores depend on artificial priors, limited coverage, and development protocols. |
| Model runtime | Three-model CPU benchmark 46104 matched scores across two chunk schedules on 56 windows per run. Processing p95 was 0.497 seconds per window with 1.66 GiB peak process RSS. The later 46108 regression suite passed 37 tests. | Live capture and concurrent throughput require separate evidence. |

## Model-only acceptance gates

| Gate | Status | Evidence needed to close it |
| --- | --- | --- |
| Reproducible LA and PA baselines | COMPLETED for the recorded protocols | Preserve checkpoint and score provenance alongside the existing independent baseline reports. |
| Audio preprocessing and abstention | COMPLETED for the tested input formats | Recovery, 8/16 kHz PCM, full-window buffering, short audio and silence checks passed. Additional codecs and transport require separate coverage. |
| Speaker verification on realistic unseen speakers | OPEN. Frozen cutoff showed high genuine rejection | CN-Celeb1 job 46189 measured 66.868% FRR and 0.385% FAR. HI-MIA job 46548 measured 22.94% FRR and 1.51% FAR, with recording-session separation unverified. Use separate development data for any candidate and a fresh session-separated assessment. Telephone support is deferred. |
| Calibrated multi-evidence risk | BLOCKED on representative labeled trials | The user approved provisional error and abstention limits. Existing research pilots lack aligned labels for the intended recording and file inputs. See the recorded-audio joint protocol for collection and evaluation. |
| Streaming model inference | COMPLETED for the authorized CPU workload | Job 46104 processed 56 windows per schedule with matching outputs across chunk schedules and batch comparisons. |
| Hindi/Hinglish robustness record | COMPLETED as a descriptive audit | Preserve the score-shift findings. Verified acquisition labels are needed before reporting Hindi/Hinglish replay error rates. |
| Model latency and memory | COMPLETED for the allocated CPU benchmark | Job 46104 measured 0.497 s p95 per window, 43.6 s model load, and 1.66 GiB peak process RSS. Live transport and service throughput require separate evidence. |
| Automated and integration checks | COMPLETED for the tested paths | Job 46108 passed 37 HPC tests, including evidence-gap reset, strict speaker cutoff parity, and the acquisition and checkpoint guards. |
| Reproducible research handoff | COMPLETED for the verified results | Benchmark metrics, scripts and artifact paths, checkpoint and threshold provenance, the inference contract, and open gate requirements are recorded below. Update the report when new evidence is verified. |

## Evidence required for the remaining validation gates

CN-Celeb1 in-the-wild audit (PBS 46189) evaluated 3,634 sampled trials
across 177 enrollment identities after excluding shared enrollment
genre/session keys. At the frozen ECAPA cutoff, FAR was 0.385% (7/1817),
FRR 66.868% (1215/1817), EER 21.051%, and AUROC 0.862942. All trials
scored. Genuine rejection was 31.53% in speech, 53.91% in interview,
and 91.59% in singing. These genre results characterize this selected
cohort. Telephone performance and ECAPA pretraining overlap remain
unverified. Preserve these scores as independent assessment evidence.

Development-only CN-Celeb1 pilot 46215 compared one versus two
enrollment references on the same validation probes. At the frozen
cutoff, AUROC improved from 0.824 to 0.901, with genuine rejects
32/40 versus 24/40 and impostor accepts 13/1560 versus 22/1560.
A two-reference candidate cutoff selected on 40 separate calibration
speakers for nominal 1% FAR yielded 19/40 genuine rejects and 49/1560
impostor accepts on validation. All trials scored. These outcomes
support further development analysis with explicit operating limits.
The frozen checkpoint, cutoff and independent assessment remain intact.

Paired review of the saved 46215 validation scores at the original cutoff
found that two references recovered 10 genuine matches and lost two.
Interview accepts rose from 5/20 to 11/20, entertainment from 0/8 to 2/8,
and singing stayed at 0/6. The other genres have at most three genuine
trials each. Of 1,560 impostor pairs, 13 became newly accepted and four
became rejected. The new accepts span 11 claims and nine probe speakers,
with at most two per claim or probe. Seven were interview, four singing,
one drama and one entertainment. Interview had 780 impostor trials, so
the raw count alone does not imply a greater genre-specific risk.

Neither two-reference operating point met the pilot's nominal 1% FAR
target on validation. The current development validation group is now
exploratory evidence for choosing follow-up experiments. For a next
candidate, predefine a maximum FAR and a minimum genuine-rejection
improvement, fit only on development calibration identities, and
evaluate once on a fresh speaker-disjoint development cohort. Preserve
the independent 46189 assessment and the existing policy.

Full CN-Celeb1 development run 46338/46347 reconciled all 60,189 planned
recordings. 60,188 were scored, one abstained and zero failed. On 298
held-out development speakers, frozen-cutoff FRR fell from 79.41% to
69.44% with two references, while FAR rose from 0.220% to 0.360%.
EER improved from 25.24% to 21.26%. The two-reference candidate cutoff
fit on 297 separate calibration speakers yielded 64.11% FRR and
0.640% FAR on 8,737,062 validation pairs. Pair counts share speakers and
probes. The remaining genuine-rejection rate precludes promotion.
Saved summary: `reports/cnceleb_full_analysis_46347.mgmt01/summary.json`.

Saved genre results show the two-reference candidate still rejected
56.6% of 13,733 interview, 72.5% of 5,346 entertainment, and 77.7% of
2,732 singing genuine trials. Singing candidate FAR was 1.16%, above
the pilot's nominal 1% pooled calibration target. For a real-channel
follow-up, compare the frozen baseline and a prespecified candidate on
matched probes. Agree on maximum FAR and FRR and minimum coverage
before scoring. Report telephone and naturally noisy conditions separately.

Access routes for the real-channel follow-up:

- [NIST SRE16 through LDC](https://catalog.ldc.upenn.edu/LDC2019S20)
  provides real 8 kHz telephone speech, trial keys and metadata.
  Confirm institutional access and permission to stage on HPC.
- [SRI SITW](https://www.sri.com/publication/speech-natural-language-pubs/the-speakers-in-the-wild-sitw-speaker-recognition-database/)
  documents naturally noisy multi-session speech. The known Hugging Face
  archive requires manual access. Confirm license and official keys.
- If neither release can be obtained promptly, use consented recordings
  with separate enrollment and test sessions, documented capture
  conditions and pseudonymous speaker IDs. Record actual calls and
  naturally noisy sessions separately. Treat a small cohort as a pilot.

Both routes still require an inventory and disjointness check before
submission. The speaker trial keys alone do not provide the synthetic
or replay labels needed for joint calibration.

On the saved CN-Celeb1 scores, 5,000 claimed-speaker bootstrap resamples
(seed 20261110, percentile intervals) gave FAR 0.11–0.74% and FRR
62.50–71.29%. At least one genuine rejection occurred for 172 of 177
claims. The intervals capture claimed-speaker variation. Reuse of some
probe speakers across claims may introduce additional dependence.

### Reproducible handoff

The current package is reviewable at seven of nine verified gates. On the
Windows machine with staged assets, run the following from the project root:

```powershell
& .\runtime_work\Start-MicrophoneDemo.ps1 -SmokeTest
```

The launcher checks both detector checkpoints and both backbone files
before offline inference. For the interactive five-second speech check,
run the same command without `-SmokeTest` and speak after pressing Enter.
Record the two raw scores, analysis time and any capture error. The pilot
keeps the microphone verdict uncertain pending calibration. A successful
speech check verifies capture and inference on that device. The real-channel
speaker and representative joint-risk evaluations require their own trial sets.

Use the HPC project root and its isolated Python environment. Match the
checkpoint and operating-point provenance below before scoring. Preserve
each existing result directory. The following entries map the verified
results to their reproduction inputs and scripts.

| Evidence | Reproduction entry | Saved result |
| --- | --- | --- |
| Independent LA baseline | Use the preserved standalone WavLM score file and official LA evaluation labels. | `scores/v3_independent_la/wavlm_la_eval.csv` |
| Independent PA baseline | Use the preserved Attention scores and official PA evaluation labels with the frozen threshold. | `scores/v3_pa_auto/selected_pa_eval.csv` and `reports/v3_pa_auto/independent_pa_eval_results.csv` |
| PA independent calibration | Pipe `audit_pa_independent.py` to the HPC project Python from its root. Reads saved scores and official protocol. | `PA_INDEPENDENT_CALIBRATION.txt` |
| Held-out speaker | `speaker_heldout_validation.pbs`, seeded official LA trial subset and frozen development cutoff | `reports/speaker_heldout_46111.mgmt01/summary.json` |
| Scoped joint pilots | `la_joint_calibration.pbs` and `pa_joint_calibration.pbs`, using existing partition artifacts | `reports/la_joint_46092.mgmt01/` and `reports/pa_joint_46098.mgmt01/` |
| CPU streaming | `three_model_stream_benchmark.pbs`, using the authorized LA development probes | `reports/stream_benchmark_46104.mgmt01/summary.json` |
| External LA transfer | `codecfake_frozen_validation.pbs`, using the CoSG manifest and frozen LA cutoff | `reports/codecfake_frozen_46063.mgmt01/summary.json` |
| Controlled speaker noise | `speaker_noise_validation.pbs`, using paired development trials | `reports/speaker_noise_46061.mgmt01/summary.json` |
| Simulated bandwidth | `bandwidth_validation.pbs`, using paired 8 and 16 kHz PCM | `reports/bandwidth_46074.mgmt01/paired_scores.csv` |
| Runtime regression | PBS 46108, scope-aware model policy checks | `logs/risk_scope_46108.mgmt01.log` |
| Local Windows model inference | Run `runtime_work/Start-MicrophoneDemo.ps1 -SmokeTest` for a tone or omit the flag for live capture. See [runtime progress](../runtime_work/PROGRESS.md). | Both pinned checkpoints scored the tone and a live five-second microphone clip. Live capture resampled from 44.1 to 16 kHz, with 14.484 s cold load and 1.605 s analysis. The microphone decision remains uncertain pending calibration. |

These entries support reproduction when justified. For a new PBS run,
verify allocation and submit through the project write lock with a
separate output directory. For local interface use, follow the
[inference contract](../runtime_work/INFERENCE_CONTRACT.md). Keep model
scores separate from operational verdicts in unsupported acquisition
conditions.

**Recorded-audio speaker robustness is blocked on authorized data.** Obtain
naturally noisy recordings with verified identities,
enrollment and probe session IDs, acquisition labels, and genuine and
impostor trial keys. Check for shared sessions or recordings across
enrollment and probe and for shared speakers with development. Record
any unverifiable ECAPA pretraining overlap. Apply the frozen 46111
cutoff and report FAR, FRR, EER, AUROC, coverage, and abstentions by
condition. Estimate uncertainty by resampling speakers where supported.
Recheck corpus availability only after an access or location change.

**Joint risk is blocked on representative aligned trials.** Each trial
needs an audio ID, speaker and session IDs,
verified acquisition scope, and labels distinguishing genuine target,
genuine impostor, synthetic and replay trials. Store all applicable model
scores for the same audio window with checkpoint digests, preprocessing
version, and abstention reasons. Split by speaker and recording session
before fitting. Apply the approved limits in the recorded-audio joint
protocol when choosing an operating point.
Freeze the policy and compare it with the existing scoped rules on a
held-out set. Include both window and session results, class-wise errors
and coverage, and behavior across missing or unreliable windows.

## Training and development diagnosis

The saved job 46010 learning curves show that the standalone WavLM run
improved discrimination while ASVspoof5 development cross-entropy grew.
The last epoch also regressed slightly from epoch 19 on both development
EERs. The figures below are saved development measurements.

| Epoch | Training loss | LA development loss | LA EER | ASVspoof5 development loss | ASVspoof5 EER |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.17923 | 0.05381 | 1.20% | 0.10463 | 3.50% |
| 10 | 0.01265 | 0.01472 | 0.25% | 0.43696 | 1.60% |
| 19 | 0.00530 | 0.01433 | 0.30% | 0.30356 | 1.45% |
| 20 | 0.00554 | 0.01240 | 0.35% | 0.33244 | 1.55% |

The current trainer uses cross-entropy on both paths, with cyclic group
sampling and optional augmentation for training and no augmentation for
development. Absolute train and development losses therefore do not form
a controlled generalization gap. Compare development trends within each
fixed domain. The ASVspoof5 loss trend and the separate temperature-scaling
result support a confidence calibration concern despite improved ranking.
They do not establish a general overfitting or underfitting conclusion.
The saved 46010 curve table covers five LA model runs and provides no
comparable PA training curve. The independent PA benchmark remains the
evidence for PA discrimination.

### PA replay diagnosis from existing evaluation

The original PA run (PBS 45797) completed 12 epochs on 54,000 training
items. The epoch-selection subset contained 2,000 of 29,700 PA development
items. Training loss fell from 0.48012 at epoch 1 to 0.25296 at epoch 12.
Selection EER improved from 10.50% to 7.05%, with a temporary rise from
7.25% at epoch 8 to 7.85% at epoch 11. Epoch 12 had the best recorded
selection EER and AUROC (0.98230). This trace shows learning and no
sustained late selection-EER deterioration. The history contains no
development loss or training EER. The saved trainer snapshot evaluates
LA and ASVspoof5, so it cannot establish the exact PA loss comparison.
Whether more training would help remains unresolved.

The selected Attention checkpoint measured 7.2551% EER and 0.98029
AUROC on full PA development, and 9.2659% EER on independent PA evaluation.
The EER difference is 2.01 percentage points. The development set was
used for model selection, so this difference combines selection effects
and possible domain shift. It cannot distinguish training overfit from
underfit. Preserve the independent benchmark and use the saved per-epoch
history to inspect loss, EER and the selected epoch before proposing training.

The frozen replay cutoff is a protocol-specific decision threshold.
EER and AUROC measure discrimination and leave probability calibration
unresolved. The high replay score exceedance on MUCS and IndicVoices
shows a score shift, with genuine false-alarm rates unknown. The PA joint
pilot's artificial priors and abstentions also limit its calibration claim.
The completed independent PA calibration audit below records the
recording-condition results at the frozen operating point.

Read-only calculation on the saved PA phase 3 grouped development scores
(`reports/v3_pa_stabilization/phase3/grouped_cv_predictions.csv`,
`score_attention` versus `label`) found 29,700 unique paths, log loss
0.163181 and Brier score 0.051297. Spoofs comprised 81.82% of this
development protocol, while the mean raw spoof score was 77.52%.
Fold log loss ranged from 0.12317 to 0.19132 and Brier from 0.03691 to
0.05985. The calculation averaged negative log likelihood with a
1e-15 floor and mean squared score error. The aggregate underprediction
describes this sample mixture. Deployment priors and condition-specific
reliability remain open. No parameters were fitted.

The read-only `audit_pa_calibration.py` check ran on HPC using the saved
29,700 PA development scores. Logistic calibration fit on four speaker
folds and scored on the fifth improved log loss in all five folds.
Pooled log loss fell from 0.163181 to 0.137746 and Brier score from
0.051297 to 0.042704. Positive slopes preserve ranking within each fold.
This demonstrates a development confidence improvement, with the
underlying checkpoint previously selected on PA development. It does
not establish backbone fitting quality or independent calibration.
The candidate remains experimental and the frozen policy stays in use.

Independent PA assessment reused 134,730 saved scores. The candidate was
fit only on development scores, with no training or development speaker
IDs shared with the assessment manifest. The official trial protocol and
manifest agreed on speaker, label and attack. Pooled log loss improved
from 0.221193 to 0.155746 and Brier from 0.070558 to 0.048964.
Both metrics improved on all nine spoof attack subsets and on 24 of
27 recording conditions. Conditions acb, acc and bcc regressed. The
genuine-only subset also regressed, from 0.230567 to 0.418930 log loss
and 0.061969 to 0.125429 Brier. Attack-only rows measure confidence
on spoofs, with no genuine comparisons within those rows.

The unchanged raw-score cutoff flagged 278 of 18,090 genuine recordings
(1.54%) and detected 90,653 of 116,640 replays (77.72%). Condition acc
had 57 genuine flags in 670 recordings (8.51%). Keep the candidate as
research evidence given the genuine-score regression. Full subgroup
results, frozen parameters and score digest are in
`PA_INDEPENDENT_CALIBRATION.txt` beside this report.

### Model assets and frozen operating points

Paths below are relative to the HPC project root. These are protocol-specific
research operating points. Apply each cutoff only to the associated raw score.

| Evidence | Asset and provenance | Frozen comparison |
| --- | --- | --- |
| LA synthetic | `checkpoints/v3_wavlm_attn_20_fixed/best.pt`. SHA-256 `5600846905b143a476ec83cd805b44536fae166102fe015ea3ed2b84e026a57b` agrees in the saved 46013 calibration and 46063 external evaluation records. | The 46013 LA raw calibration row stores `0.0061066979542373995`. The 46063 implementation read the CSV into a float and saved `0.0061066979542373`. Preserve the recorded value for exact reproduction of each run. |
| PA replay | `checkpoints/v3_pa_wavlm/best.pt`. Live HPC SHA-256 `21c4f85791204ff215dc88a3944bb53e056c614bb3f675994f33397268ba7b09`. | The PA selection record `reports/v3_pa_auto/selected_model.json` names the Attention checkpoint and freezes `0.9364579916000366`. |
| ECAPA identity | `pretrained/speaker_assets`. Pinned revision and per-file digests are recorded in `speaker_assets/PROVENANCE.json` alongside this report. | Cosine similarity strictly above `0.4769288897514343` matches. Source is `reports/speaker_evaluation_46018.mgmt01/results.json`. Job 46111 uses that cutoff and records the source digest in its summary. |

For LA, the nominal 1% calibration false-positive target yielded 3.1% on
LA selection for both the raw and temperature-scaled operating points.
In the separate ASVspoof5 comparison, both yielded 0.9% false positives
and 97.4% recall on selection. Temperature scaling changed the numeric
cutoff and improved score calibration. The observed decisions at the
matched operating points stayed the same.

The runtime adapter and tested audio formats are documented in the
[inference contract](../runtime_work/INFERENCE_CONTRACT.md). The 46104
benchmark uses the LA and PA assets above. Reproduce loading and scoring
from the saved PBS scripts and verify digests against the handoff
environment before reuse.

- Verify model identity and preprocessing against the exact training and scoring configuration. Keep checkpoint hashes, calibration source, split and threshold together.
- Diagnose the completed MUCS/IndicVoices response shift using labeled, disjoint recording conditions before considering supervised adaptation.
- Report threshold transfer, per-attack and per-speaker errors, paired uncertainty, and compute cost. Distinguish exploratory development comparisons from preserved independent benchmarks.
- Record a supported acquisition scope and explicitly report uncertainty outside it. No new training until data provenance, evaluation design, and safe allocated compute are verified.

HPC evidence is indexed in `reports/PROJECT_STATUS.md`. Recent jobs include 46048/46049 for corpus response, 46059/46060 for duration and streaming, 46061–46064 for noise and Codecfake, 46066/46071 for enrollment and model parity, 46074 for bandwidth, 46076 for trial readiness, and 46092/46093 for scoped calibration and partitioning. MUCS source and license are listed on [OpenSLR 104](https://www.openslr.org/104/). The speaker checkpoint comes from the [SpeechBrain ECAPA model card](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb).

See the [recorded audio joint protocol](RECORDED_AUDIO_JOINT_PROTOCOL.md)
for the existing-data audit and proposed limits awaiting approval.
Microphone capture and supplied-file inference are verified in the Windows
launcher. Joint decisions remain uncertain while validation is open.

See the [Windows prototype setup](../runtime_work/DEMO_SETUP.md) for
microphone capture, file input and optional ECAPA enrollment. The Windows
three-model file smoke test used one clip for both enrollment and probe
to verify integration. The 26 runtime tests passed. The joint collection
protocol records the approved provisional limits and the data needed for
independent calibration and assessment.

The live three-model Windows smoke test also passed with a fresh
microphone probe and a saved enrollment clip. See the
[runtime evidence](../runtime_work/PROGRESS.md) for scores and timings.

## HI-MIA frozen ECAPA evaluation

PBS 46548.mgmt01 completed with exit 0. The original cosine cutoff was
0.4769288897514343. All 13,605 required WAVs scored without audio failures.
Of 28,126 official trials, 27,954 scored (99.39% coverage) and 172 shared a
same-speaker utterance code and were excluded. Both protocol lists used
channel 00 for placeholders and preserved explicit channels.

| Enrollment | Scored | FAR | FRR | EER | AUROC |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pooled | 27,954 | 1.51% | 22.94% | 8.12% | 0.9704 |
| 1 meter | 13,970 | 1.96% | 19.03% | 7.77% | 0.9730 |
| Close mic | 13,984 | 1.05% | 26.84% | 8.40% | 0.9686 |

Probe codes 5 and 6 had 24.45–36.35% FRR across enrollment protocols.
Recording-session separation and person-level VoxCeleb overlap remain
unverified. This far-field wake-word benchmark leaves speaker robustness
open. Keep scores frozen and use separate development data for any changes.
HPC artifacts: reports/himia_frozen_46548.mgmt01/summary.json and trials.csv.

## J-SpAW frozen ECAPA evaluation

PBS 46565.mgmt01 exited 0. All 800 required WAVs and all 37,600
official pairs scored, with no audio failures. At the frozen cosine
cutoff 0.4769288897514343, overall FAR was 0.4433%, FRR 10.1842%,
EER 2.2632%, and AUROC 0.99756. Across 23,797 cross-room pairs, FAR
was 0.3606%, FRR 10.4333%, EER 2.1297%, and AUROC 0.99799.
The cross-room subset establishes room separation. Capture-session
separation and person-level VoxCeleb overlap are still unverified.
Keep scores fixed and retain the benchmark as external evidence.
HPC: reports/jspaw_asv_46565.mgmt01/summary.json and trials.csv.

Joint readiness: the 800 LA and 800 PA genuine controls are the same
800 ASV audio IDs. Of these, 200 are official cross-room target probes.
Count shared controls once when building joint trials. The next check is
to verify enrollment and attack source lineage, and identify separate
aligned calibration data before fitting. Seven of nine gates verified.

J-SpAW frozen LA job 46570.mgmt01 exited 0. Of 2,400 official trials,
63 (2.63%) had a full centered window and 2,337 abstained. The sole
scored genuine clip was flagged; 60 of 62 scored synthetic clips were
flagged. AUROC 0.9032 and EER 4.84% describe only the scored subset
and are not reliable deployment evidence with one genuine clip.
Keep voice-origin and joint verdicts uncertain in this scope.
Evidence: reports/jspaw_la_46570.mgmt01/summary.json and scores.jsonl.
