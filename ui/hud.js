const logEl = document.getElementById("log");
const lineEl = document.getElementById("line");
const form = document.getElementById("form");
const reactor = document.getElementById("reactor");
const verb = document.getElementById("verb");
const sysDot = document.getElementById("sys-dot");
const sysLabel = document.getElementById("sys-label");
const dVoice = document.getElementById("d-voice");
const dLink = document.getElementById("d-link");
const dChannel = document.getElementById("d-channel");

const LIVE_ENDPOINT = "https://xmkwdl0d1d.execute-api.ap-south-1.amazonaws.com/webhook";

function isLocalHost() {
  return ["localhost", "127.0.0.1", "[::1]"].includes(location.hostname);
}

function defaultEndpoint() {
  return isLocalHost() ? "/api/chat" : LIVE_ENDPOINT;
}

const cfg = {
  endpoint: localStorage.getItem("jarvis.endpoint") || defaultEndpoint(),
  token: localStorage.getItem("jarvis.token") || "",
};

const IDLE = "Ready when you are, sir";

function applyTheme(name) {
  const friday = name === "friday";
  document.body.className = friday ? "theme-friday" : "theme-jarvis";
  document.getElementById("mode-jarvis").classList.toggle("on", !friday);
  document.getElementById("mode-friday").classList.toggle("on", friday);
  document.getElementById("mark").textContent = friday ? "F.R.I.D.A.Y." : "J.A.R.V.I.S.";
  document.getElementById("sub").textContent = friday
    ? "Female Replacement Intelligent Digital Assistant Youth"
    : "Just A Rather Very Intelligent System";
  document.getElementById("boot-mark").textContent = friday ? "F.R.I.D.A.Y." : "J.A.R.V.I.S.";
  document.title = friday ? "F.R.I.D.A.Y." : "J.A.R.V.I.S.";
  localStorage.setItem("jarvis.theme", friday ? "friday" : "jarvis");
}

applyTheme(localStorage.getItem("jarvis.theme") || "jarvis");
document.getElementById("mode-jarvis").addEventListener("click", () => applyTheme("jarvis"));
document.getElementById("mode-friday").addEventListener("click", () => applyTheme("friday"));

(function paintTicks() {
  const root = document.querySelector(".ticks-svg");
  const proto = document.getElementById("tick");
  if (!root || !proto) return;
  for (let a = 10; a < 360; a += 10) {
    const g = proto.cloneNode(true);
    g.removeAttribute("id");
    g.setAttribute("transform", `rotate(${a} 200 200)`);
    root.appendChild(g);
  }
})();

function setState(name, label) {
  reactor.className = "rings " + (name || "");
  verb.textContent = label;
  sysDot.className = "dot " + (name === "think" || name === "speak" ? "busy" : name === "listen" ? "live" : "");
  sysLabel.textContent =
    name === "think" ? "One moment" : name === "listen" ? "Listening" : name === "speak" ? "Speaking" : "At ease";
  dVoice.textContent = name === "listen" ? "Listening" : name === "speak" ? "Speaking" : "Quiet";
}

function md(text) {
  const esc = String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  return esc
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

function addMsg(who, text, buttons) {
  const wrap = document.createElement("article");
  wrap.className = "msg " + (who === "you" ? "you" : "jarvis");
  wrap.innerHTML = `<div class="who">${who === "you" ? "You" : "J.A.R.V.I.S."}</div><div class="body">${md(text)}</div>`;
  if (buttons && buttons.length) {
    const acts = document.createElement("div");
    acts.className = "acts";
    for (const b of buttons) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = b.label;
      btn.addEventListener("click", () => send({ callback: b.data }));
      acts.appendChild(btn);
    }
    wrap.appendChild(acts);
  }
  logEl.appendChild(wrap);
  logEl.scrollTop = logEl.scrollHeight;
}

function pickVoice() {
  const voices = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
  const want = [
    /daniel.*united kingdom/i,
    /daniel \(english \(united kingdom\)\)/i,
    /^daniel$/i,
    /google uk english male/i,
    /microsoft george/i,
    /arthur/i,
    /george.*uk|uk.*george/i,
  ];
  for (const re of want) {
    const hit = voices.find((v) => re.test(v.name));
    if (hit) return hit;
  }
  return (
    voices.find((v) => /en-GB/i.test(v.lang) && !/female|susan|serena|kate|martha|moira/i.test(v.name)) ||
    voices.find((v) => /en-GB/i.test(v.lang)) ||
    null
  );
}

function forSpeech(text) {
  let spoken = String(text || "")
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/[*_`#|]/g, " ")
    .replace(/https?:\/\/\S+/g, " ")
    .replace(/\bokay\b/gi, "very well")
    .replace(/\bOK\b/g, "very well")
    .replace(/\bgonna\b/gi, "going to")
    .replace(/\bgot it\b/gi, "understood")
    .replace(/\bsure thing\b/gi, "of course")
    .replace(/\bno problem\b/gi, "of course")
    .replace(/\blet's\b/gi, "shall we")
    .replace(/\s+/g, " ")
    .trim();
  if (!spoken) return "Nothing to report, sir.";
  const parts = spoken.split(/(?<=[.!?])\s+/).filter(Boolean);
  spoken = parts.slice(0, 3).join(" ");
  if (spoken.length > 380) {
    const cut = spoken.slice(0, 380);
    const stop = Math.max(cut.lastIndexOf(". "), cut.lastIndexOf("? "));
    spoken = stop > 40 ? cut.slice(0, stop + 1) : cut;
  }
  return spoken;
}

function speak(text) {
  if (!text || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(forSpeech(text));
  u.lang = "en-GB";
  u.rate = 0.88;
  u.pitch = 0.78;
  u.volume = 1;
  const voice = pickVoice();
  if (voice) u.voice = voice;
  u.onstart = () => setState("speak", "Speaking");
  u.onend = () => {
    if (listenMode && !busy) resumeListen();
    else setState("", IDLE);
  };
  window.speechSynthesis.speak(u);
}

if (window.speechSynthesis) {
  window.speechSynthesis.onvoiceschanged = pickVoice;
  pickVoice();
}

let listenMode = false;
let busy = false;

async function send(payload) {
  const outgoing = payload.text || "";
  if (outgoing) addMsg("you", outgoing);
  busy = true;
  setState("think", "One moment");
  try {
    const headers = { "Content-Type": "application/json" };
    const body = { event: "desk_chat", ...payload };
    if (cfg.token) {
      headers["x-desk-token"] = cfg.token;
      body.token = cfg.token;
    }
    const res = await fetch(cfg.endpoint, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok || data.ok === false) {
      throw new Error(data.error || res.statusText || "the line failed");
    }
    addMsg("jarvis", data.text || "Nothing to add, sir.", data.buttons);
    speak(data.speak || data.text);
    dLink.textContent = "Connected";
    sysDot.className = "dot live";
  } catch (err) {
    addMsg("jarvis", "I'm afraid I can't reach the house brain. " + err.message);
    dLink.textContent = "Down";
    sysDot.className = "dot bad";
    setState("", "I'm afraid the line is down");
    speak("I'm afraid I can't reach the house brain, sir.");
    busy = false;
    if (listenMode) resumeListen();
    return;
  }
  busy = false;
  if (listenMode) resumeListen();
  else setState("", IDLE);
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = lineEl.value.trim();
  if (!text) return;
  lineEl.value = "";
  send({ text });
});

document.getElementById("quick").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-cmd]");
  if (btn) send({ text: btn.dataset.cmd });
});

const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
let rec = null;
let recArmed = false;
if (Speech) {
  rec = new Speech();
  rec.lang = "en-IN";
  rec.continuous = true;
  rec.interimResults = true;
  rec.onresult = (ev) => {
    let interim = "";
    let finalText = "";
    for (let n = ev.resultIndex; n < ev.results.length; n += 1) {
      const bit = ev.results[n][0].transcript.trim();
      if (ev.results[n].isFinal) finalText += (finalText ? " " : "") + bit;
      else interim += (interim ? " " : "") + bit;
    }
    if (interim) {
      lineEl.value = interim;
      setState("listen", interim);
    }
    if (finalText && !busy) {
      lineEl.value = "";
      window.speechSynthesis.cancel();
      send({ text: finalText });
    }
  };
  rec.onerror = (ev) => {
    if (ev.error === "not-allowed") {
      listenMode = false;
      addMsg("jarvis", "The microphone is blocked, sir. Allow it for this page, then click the core again.");
      speak("The microphone is blocked, sir.");
      setState("", IDLE);
      return;
    }
    if (listenMode && ev.error !== "aborted") resumeListen();
  };
  rec.onend = () => {
    recArmed = false;
    if (listenMode && !busy) resumeListen();
  };
}

let mediaStream = null;
let recorder = null;
let recChunks = [];
let recWatch = null;
let spokenSeen = false;

function pickMime() {
  const types = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
  for (const t of types) {
    if (window.MediaRecorder && MediaRecorder.isTypeSupported(t)) return t;
  }
  return "";
}

async function transcribeBlob(blob) {
  if (!isLocalHost()) {
    throw new Error("use the browser ear on the public site");
  }
  const res = await fetch("/api/transcribe", {
    method: "POST",
    headers: { "Content-Type": blob.type || "audio/webm" },
    body: blob,
  });
  const data = await res.json();
  if (!res.ok || data.ok === false) throw new Error(data.error || "I couldn't make that out");
  return (data.text || "").trim();
}

function startRecorder() {
  if (!mediaStream || !window.MediaRecorder) return;
  const mime = pickMime();
  recChunks = [];
  spokenSeen = false;
  recorder = mime ? new MediaRecorder(mediaStream, { mimeType: mime }) : new MediaRecorder(mediaStream);
  recorder.ondataavailable = (e) => {
    if (e.data && e.data.size) recChunks.push(e.data);
  };
  recorder.onstop = async () => {
    if (!listenMode || busy) return;
    const blob = new Blob(recChunks, { type: recorder.mimeType || "audio/webm" });
    recChunks = [];
    if (blob.size < 2000) {
      if (listenMode) startRecorder();
      return;
    }
    setState("think", "Making that out");
    try {
      const said = await transcribeBlob(blob);
      if (said && !busy) {
        lineEl.value = "";
        send({ text: said });
        return;
      }
    } catch (err) {
      addMsg("jarvis", "I'm afraid I didn't catch that. " + err.message);
    }
    if (listenMode && !busy) startRecorder();
  };
  recorder.start(200);
  const ctx = new AudioContext();
  const src = ctx.createMediaStreamSource(mediaStream);
  const anal = ctx.createAnalyser();
  anal.fftSize = 512;
  src.connect(anal);
  const buf = new Uint8Array(anal.frequencyBinCount);
  let quiet = 0;
  clearInterval(recWatch);
  recWatch = setInterval(() => {
    anal.getByteTimeDomainData(buf);
    let sum = 0;
    for (const v of buf) {
      const n = (v - 128) / 128;
      sum += n * n;
    }
    const rms = Math.sqrt(sum / buf.length);
    if (rms > 0.045) {
      spokenSeen = true;
      quiet = 0;
      setState("listen", "I'm listening");
    } else if (spokenSeen) {
      quiet += 1;
      if (quiet >= 8 && recorder && recorder.state === "recording") {
        spokenSeen = false;
        quiet = 0;
        recorder.stop();
      }
    }
  }, 120);
}

async function armMic() {
  if (mediaStream) return mediaStream;
  mediaStream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true },
  });
  return mediaStream;
}

function resumeListen() {
  if (!listenMode || busy) return;
  setState("listen", "I'm listening");
  if (rec) {
    try {
      if (!recArmed) {
        rec.start();
        recArmed = true;
      }
    } catch (_) {
      recArmed = true;
    }
    return;
  }
  if (recorder && recorder.state === "recording") return;
  startRecorder();
}

async function toggleListen() {
  if (listenMode) {
    listenMode = false;
    recArmed = false;
    try {
      rec && rec.stop();
    } catch (_) {
      /* ignore */
    }
    if (recorder && recorder.state === "recording") recorder.stop();
    clearInterval(recWatch);
    window.speechSynthesis.cancel();
    setState("", IDLE);
    return;
  }
  window.speechSynthesis.cancel();
  try {
    await armMic();
  } catch (_) {
    addMsg("jarvis", "I need the microphone, sir. Allow it for this page, then click the core.");
    speak("I need the microphone, sir.");
    return;
  }
  listenMode = true;
  setState("listen", "I'm listening");
  if (!rec) startRecorder();
  else resumeListen();
}

document.getElementById("mic").addEventListener("click", toggleListen);
window.addEventListener("keydown", (e) => {
  if (e.code === "Space" && document.activeElement !== lineEl && !e.repeat) {
    e.preventDefault();
    toggleListen();
  }
});

function hms(hours, minutes, seconds) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
}

function tick() {
  const now = new Date();
  const utcH = now.getUTCHours();
  const utcM = now.getUTCMinutes();
  const utcS = now.getUTCSeconds();
  const ist = new Date(now.getTime() + (5 * 60 + 30) * 60 * 1000);
  document.getElementById("clock-utc").textContent = hms(utcH, utcM, utcS);
  document.getElementById("clock-ist").textContent = hms(
    ist.getUTCHours(),
    ist.getUTCMinutes(),
    ist.getUTCSeconds(),
  );
}
setInterval(tick, 1000);
tick();

const dlg = document.getElementById("settings");
document.getElementById("btn-settings").addEventListener("click", () => {
  document.getElementById("cfg-endpoint").value = cfg.endpoint;
  document.getElementById("cfg-token").value = cfg.token;
  dlg.showModal();
});
document.getElementById("cfg-save").addEventListener("click", (e) => {
  e.preventDefault();
  cfg.endpoint = document.getElementById("cfg-endpoint").value.trim() || defaultEndpoint();
  cfg.token = document.getElementById("cfg-token").value.trim();
  localStorage.setItem("jarvis.endpoint", cfg.endpoint);
  localStorage.setItem("jarvis.token", cfg.token);
  dChannel.textContent = cfg.endpoint === "/api/chat" ? "This machine" : "The live house";
  dlg.close();
  pingLine();
});

dChannel.textContent = cfg.endpoint === "/api/chat" ? "This machine" : "The live house";

function pingLine() {
  fetch(cfg.endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event: "desk_chat", text: "ping" }),
  })
    .then((res) => {
      if (res.ok || res.status === 401) {
        dLink.textContent = "Connected";
        sysDot.className = "dot live";
        return;
      }
      throw new Error(String(res.status));
    })
    .catch(() => {
      dLink.textContent = "Down";
      sysDot.className = "dot bad";
    });
}
pingLine();

const boot = document.getElementById("boot");
const bootLine = document.getElementById("boot-line");
const steps = ["Initialising, sir", "Almost there", "Ready"];
let i = 0;
const bootTimer = setInterval(() => {
  bootLine.textContent = steps[i] || "Ready";
  i += 1;
  if (i > steps.length) {
    clearInterval(bootTimer);
    boot.classList.add("gone");
    setState("", IDLE);
    addMsg("jarvis", "At your service, sir.");
    if (!isLocalHost() && !cfg.token) {
      addMsg("jarvis", "The house is live. Open Preferences and paste the desk token from your local .env — it stays in this browser.");
    }
    speak("At your service, sir.");
  }
}, 480);
