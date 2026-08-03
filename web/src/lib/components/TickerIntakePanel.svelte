<script lang="ts">
  import type { ListKind, WatchlistIntakeResponse } from "../types";

  interface Props {
    busy?: boolean;
    listKind?: ListKind;
    onintake: (text: string, listKind: ListKind) => Promise<WatchlistIntakeResponse | void>;
  }

  let {
    busy = false,
    listKind = $bindable("watched" as ListKind),
    onintake,
  }: Props = $props();

  let open = $state(false);
  let text = $state("");
  let localBusy = $state(false);
  let ocrBusy = $state(false);
  let listening = $state(false);
  let statusMsg = $state<string | null>(null);
  let lastResult = $state<WatchlistIntakeResponse | null>(null);
  let fileInput: HTMLInputElement | undefined = $state();
  let imageInput: HTMLInputElement | undefined = $state();
  let recognition: SpeechRecognition | null = null;

  const isBusy = $derived(busy || localBusy || ocrBusy);

  function summarize(r: WatchlistIntakeResponse): string {
    const parts = [
      `Added ${r.added_count}`,
      `skipped ${r.skipped_duplicate_count} duplicate`,
      `rejected ${r.rejected_invalid_count} invalid`,
    ];
    return parts.join(" · ");
  }

  async function submit() {
    if (isBusy || !text.trim()) return;
    localBusy = true;
    statusMsg = null;
    lastResult = null;
    try {
      const res = await onintake(text, listKind);
      if (res) {
        lastResult = res;
        statusMsg = summarize(res);
        if (res.added_count > 0) text = "";
      }
    } catch (e) {
      statusMsg = e instanceof Error ? e.message : String(e);
    } finally {
      localBusy = false;
    }
  }

  async function onCsvFile(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    statusMsg = null;
    try {
      const content = await file.text();
      text = text.trim() ? `${text.trim()}\n${content}` : content;
      statusMsg = `Loaded ${file.name}`;
    } catch (err) {
      statusMsg = err instanceof Error ? err.message : String(err);
    } finally {
      input.value = "";
    }
  }

  async function onImageFile(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    statusMsg = null;
    ocrBusy = true;
    try {
      const { createWorker } = await import("tesseract.js");
      const worker = await createWorker("eng");
      try {
        const {
          data: { text: ocrText },
        } = await worker.recognize(file);
        const cleaned = (ocrText || "").trim();
        if (!cleaned) {
          statusMsg = "No text found in image.";
        } else {
          text = text.trim() ? `${text.trim()}\n${cleaned}` : cleaned;
          statusMsg = `OCR from ${file.name}`;
        }
      } finally {
        await worker.terminate();
      }
    } catch (err) {
      statusMsg =
        err instanceof Error
          ? `OCR failed: ${err.message}`
          : "OCR failed. Paste tickers as text instead.";
    } finally {
      ocrBusy = false;
      input.value = "";
    }
  }

  function toggleSpeech() {
    const SR =
      window.SpeechRecognition ||
      (window as unknown as { webkitSpeechRecognition?: typeof SpeechRecognition })
        .webkitSpeechRecognition;
    if (!SR) {
      statusMsg = "Speech recognition is not supported in this browser.";
      return;
    }
    if (listening && recognition) {
      recognition.stop();
      return;
    }
    const rec = new SR();
    recognition = rec;
    rec.lang = "en-US";
    rec.interimResults = false;
    rec.continuous = false;
    rec.onstart = () => {
      listening = true;
      statusMsg = "Listening… speak tickers (e.g. NVDA AAPL MSFT)";
    };
    rec.onerror = () => {
      listening = false;
      statusMsg = "Speech recognition error. Try paste or CSV.";
    };
    rec.onend = () => {
      listening = false;
      recognition = null;
    };
    rec.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = Array.from(event.results)
        .map((r) => r[0]?.transcript ?? "")
        .join(" ")
        .trim();
      if (transcript) {
        text = text.trim() ? `${text.trim()} ${transcript}` : transcript;
        statusMsg = "Speech captured — review and Import.";
      }
    };
    rec.start();
  }
</script>

<div class="intake">
  <button
    type="button"
    class="toggle"
    class:open
    disabled={busy}
    aria-expanded={open}
    onclick={() => (open = !open)}
  >
    {open ? "Hide import" : "Import tickers"}
  </button>

  {#if open}
    <div class="panel">
      <p class="hint">
        Paste symbols, upload CSV, speak, or OCR a screenshot. Duplicates are
        skipped. Research stays off until you refresh.
      </p>
      <div class="row">
        <label class="kind">
          Add to
          <select bind:value={listKind} disabled={isBusy} aria-label="Import list kind">
            <option value="watched">Watched</option>
            <option value="held">Held</option>
          </select>
        </label>
        <button
          type="button"
          class="secondary"
          disabled={isBusy}
          onclick={() => fileInput?.click()}
        >
          CSV file
        </button>
        <button
          type="button"
          class="secondary"
          disabled={isBusy}
          onclick={() => imageInput?.click()}
        >
          {ocrBusy ? "Reading image…" : "Screenshot"}
        </button>
        <button
          type="button"
          class="secondary"
          class:listening
          disabled={isBusy && !listening}
          onclick={toggleSpeech}
        >
          {listening ? "Stop" : "Speak"}
        </button>
      </div>
      <input
        bind:this={fileInput}
        type="file"
        accept=".csv,text/csv,text/plain"
        class="sr"
        onchange={onCsvFile}
      />
      <input
        bind:this={imageInput}
        type="file"
        accept="image/*"
        class="sr"
        onchange={onImageFile}
      />
      <label class="sr-label">
        Tickers
        <textarea
          bind:value={text}
          rows={4}
          disabled={isBusy}
          placeholder="NVDA, AAPL, MSFT — or paste a broker export"
          spellcheck="false"
        ></textarea>
      </label>
      <div class="actions">
        <button
          type="button"
          class="import"
          disabled={isBusy || !text.trim()}
          onclick={() => void submit()}
        >
          {localBusy ? "Importing…" : "Import"}
        </button>
      </div>
      {#if statusMsg}
        <p class="status" aria-live="polite">{statusMsg}</p>
      {/if}
      {#if lastResult && lastResult.rejected_invalid.length > 0}
        <p class="rejects">
          Rejected: {lastResult.rejected_invalid.slice(0, 12).join(", ")}
          {#if lastResult.rejected_invalid.length > 12}
            …
          {/if}
        </p>
      {/if}
    </div>
  {/if}
</div>

<style>
  .intake {
    width: 100%;
  }
  .toggle {
    border: 1px solid var(--line);
    background: white;
    color: var(--ink);
    border-radius: 2px;
    padding: 0.55rem 0.75rem;
    min-height: 44px;
    font-weight: 500;
  }
  .toggle.open {
    box-shadow: inset 0 -2px 0 var(--accent);
  }
  .panel {
    margin-top: 0.65rem;
    padding: 0.85rem 0;
    border-top: 1px solid var(--line);
  }
  .hint {
    margin: 0 0 0.75rem;
    color: var(--ink-soft);
    font-size: 0.9rem;
    max-width: 40rem;
    line-height: 1.45;
  }
  .row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    align-items: center;
    margin-bottom: 0.65rem;
  }
  .kind {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    color: var(--ink-soft);
    font-size: 0.9rem;
  }
  select,
  .secondary,
  .import {
    border: 1px solid var(--line);
    background: white;
    color: var(--ink);
    border-radius: 2px;
    padding: 0.55rem 0.75rem;
    min-height: 44px;
  }
  .secondary.listening {
    border-color: var(--accent);
    color: var(--accent);
  }
  .import {
    background: var(--ink);
    color: var(--paper);
    border-color: var(--ink);
    font-weight: 500;
  }
  .import:disabled,
  .secondary:disabled,
  .toggle:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .sr {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
  }
  .sr-label {
    display: block;
  }
  textarea {
    display: block;
    width: 100%;
    margin-top: 0.35rem;
    border: 1px solid var(--line);
    border-radius: 2px;
    padding: 0.65rem 0.75rem;
    background: white;
    color: var(--ink);
    font-family: var(--font-body);
    letter-spacing: 0.02em;
    resize: vertical;
    min-height: 6rem;
  }
  .actions {
    margin-top: 0.55rem;
  }
  .status {
    margin: 0.55rem 0 0;
    color: var(--ink-soft);
    font-size: 0.9rem;
  }
  .rejects {
    margin: 0.35rem 0 0;
    color: var(--error);
    font-size: 0.85rem;
  }
</style>
