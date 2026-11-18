/* eslint-disable */
// Offline AI translator (Opus-MT English->Indonesian) running inside the phone/browser. No server, no credits.
import { pipeline, env } from "./transformers.min.js";

// runtime files sit next to this worker (APK, own server, preview all send correct MIME types)
env.backends.onnx.wasm.wasmPaths = new URL("./", self.location.href).href;
env.backends.onnx.wasm.numThreads = 1;
env.useBrowserCache = true;

let tr = null;

self.onmessage = async (e) => {
  const { id, texts, localModels } = e.data;
  try {
    if (!tr) {
      env.allowLocalModels = !!localModels;
      env.localModelPath = new URL("../models/", self.location.href).href;
      env.allowRemoteModels = true;
      tr = await pipeline("translation", "Xenova/opus-mt-en-id", {
        dtype: "q8",
        progress_callback: (p) => { if (p.status === "progress") self.postMessage({ progress: Math.round(p.progress || 0), file: p.file }); },
      });
    }
    const out = [];
    for (const t of texts || []) out.push(t ? (await tr(t, { max_new_tokens: 160 }))[0].translation_text : "");
    self.postMessage({ id, out });
  } catch (err) {
    self.postMessage({ id, error: String(err && err.message || err) });
  }
};
