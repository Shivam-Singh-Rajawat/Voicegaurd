"use strict";

const $ = (id) => document.getElementById(id);
const MAX_BYTES = 16 * 1024 * 1024;
const DURATION_MS = 12000;
let selectedAudio = null;
let capture = null;
let lastReport = null;
let modelReady = false;
let speakerReady = false;

function setMessage(text, error = false) {
  $("actionStatus").textContent = text;
  $("actionStatus").classList.toggle("error", error);
}

function validAudio(file) {
  return file && /\.(wav|flac|ogg|mp3)$/i.test(file.name) && file.size > 0 && file.size <= MAX_BYTES;
}

function selectAudio(file, description) {
  if (!validAudio(file)) {
    selectedAudio = null;
    $("selectionStatus").textContent = "Choose nonempty WAV, FLAC, OGG or MP3 audio under 16 MB.";
    setMessage("Unsupported file or size limit exceeded.", true);
  } else {
    selectedAudio = file;
    $("selectionStatus").textContent = description + " • " + (file.size / (1024 * 1024)).toFixed(2) + " MB";
    setMessage("Ready to analyze. The recording is never uploaded to a cloud service.");
  }
  $("audioFile").parentElement.classList.toggle("has-file", Boolean(selectedAudio));
  $("analyzeBtn").disabled = !selectedAudio || !modelReady || Boolean(capture);
}

$("audioFile").addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (file) selectAudio(file, "Selected file: " + file.name);
});
$("scanCheck").addEventListener("change", () => {
  if (!$("scanCheck").checked) {
    $("replayCheck").checked = false;
  }
  $("replayCheck").disabled = !$("scanCheck").checked;
});

function encodeWav(parts, rate) {
  const length = parts.reduce((sum, part) => sum + part.length, 0);
  const dataLength = length * 2;
  const buffer = new ArrayBuffer(44 + dataLength);
  const view = new DataView(buffer);
  const writeText = (offset, text) => {
    for (let i = 0; i < text.length; i++) view.setUint8(offset + i, text.charCodeAt(i));
  };
  writeText(0, "RIFF");
  view.setUint32(4, 36 + dataLength, true);
  writeText(8, "WAVE");
  writeText(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, rate, true);
  view.setUint32(28, rate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeText(36, "data");
  view.setUint32(40, dataLength, true);
  let cursor = 44;
  for (const part of parts) {
    for (const value of part) {
      const s = Math.max(-1, Math.min(1, value));
      view.setInt16(cursor, s < 0 ? Math.round(s * 32768) : Math.round(s * 32767), true);
      cursor += 2;
    }
  }
  return new Blob([buffer], {type: "audio/wav"});
}

async function finishRecording() {
  const session = capture;
  if (!session) return;
  capture = null;
  window.clearTimeout(session.timeout);
  window.clearInterval(session.interval);
  session.node.onaudioprocess = null;
  session.node.disconnect();
  session.source.disconnect();
  session.stream.getTracks().forEach(track => track.stop());
  await session.context.close();

  $("recordBtn").textContent = "●  Record 12 seconds";
  $("recordBtn").disabled = false;
  $("recordCountdown").textContent = "";
  const total = session.parts.reduce((count, p) => count + p.length, 0);
  if (total < session.context.sampleRate * 4.0375) {
    setMessage("Recording was too short. Record at least 8 seconds of clear speech.", true);
    $("analyzeBtn").disabled = !selectedAudio || !modelReady;
    return;
  }
  const blob = encodeWav(session.parts, session.context.sampleRate);
  const file = new File([blob], "microphone.wav", {type: "audio/wav"});
  $("audioFile").value = "";
  selectAudio(file, "Local microphone capture: " + (total / session.context.sampleRate).toFixed(1) + " seconds");
}

async function startRecording() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setMessage("Microphone capture requires a supported browser at http://127.0.0.1:8765.", true);
    return;
  }
  let stream = null;
  let context = null;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: {channelCount: 1, echoCancellation: false,
              noiseSuppression: false, autoGainControl: false}
    });
    context = new window.AudioContext();
    await context.resume();
    const source = context.createMediaStreamSource(stream);
    const node = context.createScriptProcessor(4096, 1, 1);
    const parts = [];
    node.onaudioprocess = (event) => {
      parts.push(new Float32Array(event.inputBuffer.getChannelData(0)));
    };
    source.connect(node);
    node.connect(context.destination);
    const start = performance.now();
    capture = {stream, context, source, node, parts, timeout: null, interval: null};
    $("recordBtn").textContent = "■  Stop & use recording";
    $("analyzeBtn").disabled = true;
    setMessage("Recording locally. Speak for at least 8 seconds. No data is uploaded.");
    capture.interval = window.setInterval(() => {
      $("recordCountdown").textContent = Math.max(0, Math.ceil(
        (DURATION_MS - (performance.now() - start)) / 1000
      )) + " seconds remaining";
    }, 250);
    capture.timeout = window.setTimeout(finishRecording, DURATION_MS);
  } catch (error) {
    if (stream) stream.getTracks().forEach(track => track.stop());
    if (context) await context.close();
    setMessage("Microphone unavailable or permission denied: " + error.message, true);
  }
}
$("recordBtn").addEventListener("click", () => capture ? finishRecording() : startRecording());

function formatScore(value) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(6) : "—";
}
function evidenceNote(evidence) {
  if (!evidence || evidence === "unavailable") return "Not available";
  if (evidence.status === "insufficient_audio") return "Insufficient full-window audio";
  if (evidence.status === "no_signal") return "No signal";
  if (evidence.score === null) return "No valid score";
  return "Raw diagnostic evidence";
}
function setMetric(scoreId, noteId, value, note) {
  $(scoreId).textContent = formatScore(value);
  $(noteId).textContent = note;
}

function timelineEntries(report) {
  const entries = [];
  for (const [key, kind] of [["synthetic_file_scan", "Synthetic"],
                            ["replay_file_scan", "Replay"]]) {
    const scan = report[key];
    if (scan && Array.isArray(scan.windows)) {
      for (const window of scan.windows) {
        entries.push({kind, start: window.start_seconds,
                      end: window.end_seconds, score: window.score});
      }
    }
  }
  return entries.sort((a,b) => a.start - b.start || a.kind.localeCompare(b.kind));
}

function renderTimeline(report) {
  const timeline = $("timeline");
  const entries = timelineEntries(report);
  timeline.replaceChildren();
  if (entries.length === 0) {
    timeline.className = "timeline-empty";
    timeline.textContent = "No complete windows were scanned, or window scanning was disabled.";
    return;
  }
  timeline.className = "timeline-list";
  for (const entry of entries.slice(0, 90)) {
    const row = document.createElement("div");
    row.className = "window-row";
    const label = document.createElement("span");
    label.textContent = entry.kind + " " + entry.start.toFixed(1) + "–" + entry.end.toFixed(1) + "s";
    const meter = document.createElement("progress");
    meter.className = entry.kind === "Replay" ? "replay-meter" : "synthetic-meter";
    meter.max = 1;
    meter.value = typeof entry.score === "number" ? entry.score : 0;
    meter.setAttribute("aria-label", entry.kind + " raw score");
    const value = document.createElement("span");
    value.className = "window-value";
    value.textContent = formatScore(entry.score);
    row.append(label, meter, value);
    timeline.append(row);
  }
  if (entries.length > 90) {
    const more = document.createElement("p");
    more.textContent = "Showing the first 90 windows; the exported JSON contains all " + entries.length + ".";
    timeline.append(more);
  }
}

function renderReport(report) {
  lastReport = report;
  $("downloadBtn").disabled = false;
  const predicted = report.prediction || {label: "Unknown", status: "missing",
    reason: "The model did not supply a verified prediction label."};
  $("predictionLabel").textContent = predicted.label;
  $("predictionStatus").textContent = predicted.status !== "provisional"
    ? "ABSTAINED" : predicted.label === "Human"
    ? "UNRELIABLE NEGATIVE" : "UNVERIFIED PREDICTION";
  $("predictionReason").textContent = predicted.reason + " " +
    (predicted.validation_warning || "") +
    " Security decision: uncertain. Label is not a probability or confirmed ground truth.";
  $("verdictText").textContent = "Uncertain";
  $("verdictIcon").textContent = "?";
  $("verdictReason").textContent = report.reason ||
    "The detectors do not support a validated binary verdict for this recording.";
  const synthetic = report.evidence && report.evidence.synthetic;
  const replay = report.evidence && report.evidence.replay;
  setMetric("syntheticScore", "syntheticNote", synthetic && synthetic.score, evidenceNote(synthetic));
  setMetric("replayScore", "replayNote", replay && replay.score, evidenceNote(replay));
  const speaker = report.speaker_verification;
  if (typeof speaker === "object" && speaker !== null) {
    setMetric("speakerScore", "speakerNote", speaker.similarity,
              (report.prediction && report.prediction.speaker_prediction &&
               report.prediction.speaker_prediction !== "Unknown"
               ? report.prediction.speaker_prediction + " — research-only"
               : speaker.status || "Research speaker comparison"));
  } else {
    setMetric("speakerScore", "speakerNote", null, "No speaker reference provided");
  }
  renderTimeline(report);
  $("results").scrollIntoView({behavior: "smooth", block: "start"});
}

$("analyzeBtn").addEventListener("click", async () => {
  if (!selectedAudio || !modelReady) return;
  if (!validAudio(selectedAudio)) return setMessage("Invalid audio source.", true);
  const reference = $("referenceFile").files[0];
  if (reference && !validAudio(reference)) return setMessage("Invalid enrollment audio file.", true);
  const params = new URLSearchParams();
  if ($("scanCheck").checked) params.set("scan", "true");
  if ($("replayCheck").checked) params.set("scan_replay", "true");
  const form = new FormData();
  form.append("file", selectedAudio, selectedAudio.name);
  if (reference) form.append("reference", reference, reference.name);
  const button = $("analyzeBtn");
  button.disabled = true;
  button.textContent = "Analyzing locally…";
  setMessage("Scoring the recording with frozen research models. Longer scans may take more time.");
  try {
    const response = await fetch("/analyze?" + params, {method: "POST", body: form});
    const report = await response.json();
    if (!response.ok) {
      throw new Error(typeof report.detail === "string" ? report.detail : "Analysis failed");
    }
    renderReport(report);
    setMessage("Analysis complete. Inspect the raw scores and export the report if needed.");
  } catch (error) {
    setMessage(error.message, true);
  } finally {
    button.disabled = !modelReady || !selectedAudio;
    button.textContent = "Run voice analysis ↗";
  }
});

$("downloadBtn").addEventListener("click", () => {
  if (!lastReport) return;
  const blob = new Blob([JSON.stringify(lastReport, null, 2) + "\n"],
                        {type: "application/json"});
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "voicegaurd-evidence-" + new Date().toISOString().replace(/[:.]/g, "-") + ".json";
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 2000);
});

async function initialize() {
  try {
    const response = await fetch("/health", {cache: "no-store"});
    if (!response.ok) throw new Error("Health endpoint unavailable");
    const health = await response.json();
    modelReady = health.status === "ready";
    speakerReady = health.speaker_verification === "ready";
    $("backendStatus").textContent = modelReady ? "Models loaded · offline" : "Models not loaded";
    $("speakerStatus").textContent = speakerReady ? "Model ready" : "Unavailable (optional)";
    $("referenceFile").disabled = !speakerReady;
    $("analyzeBtn").disabled = !modelReady || !selectedAudio;
    if (!modelReady) setMessage("Models not loaded. Check the local server console.", true);
  } catch (error) {
    $("backendStatus").textContent = "Server connection lost";
    setMessage("Cannot reach the local model server.", true);
  }
}
initialize();
