"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { uploadToCloudinary } from "../lib/uploadToCloudinary";

type AnalyzeResponse = {
  requestId: string;
  overall: {
    label: "likely_scam" | "uncertain" | "likely_legit";
    score: number;
    confidence: "Low" | "Medium" | "High";
    summary: string;
    recommendations: string[];
  };
  agents: Array<{
    name: string;
    focus: string;
    finding: string;
    signals: string[];
  }>;
};

function labelBadge(label: AnalyzeResponse["overall"]["label"]) {
  switch (label) {
    case "likely_scam":
      return "border border-red-500/25 bg-red-500/10 text-red-700 dark:text-red-300";
    case "uncertain":
      return "border border-amber-500/25 bg-amber-500/10 text-amber-800 dark:text-amber-200";
    case "likely_legit":
      return "border border-emerald-500/25 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200";
    default:
      return "border border-border bg-muted text-muted-foreground";
  }
}

function labelBar(label: AnalyzeResponse["overall"]["label"]) {
  switch (label) {
    case "likely_scam":
      return "bg-red-600";
    case "uncertain":
      return "bg-amber-500";
    case "likely_legit":
      return "bg-emerald-600";
    default:
      return "bg-foreground";
  }
}

function formatLabel(label: AnalyzeResponse["overall"]["label"]) {
  return label.replaceAll("_", " ");
}

export default function Home() {
  const [text, setText] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [uploadedImageUrl, setUploadedImageUrl] = useState<string | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [showScreenshot, setShowScreenshot] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [theme, setTheme] = useState<"light" | "dark" | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const canAnalyze = useMemo(
    () => (text.trim().length > 0 || !!imageFile || !!uploadedImageUrl) && !isLoading && !isUploading,
    [text, isLoading, isUploading, imageFile, uploadedImageUrl]
  );

  useEffect(() => {
    const isDark = document.documentElement.classList.contains("dark");
    setTheme(isDark ? "dark" : "light");
  }, []);

  useEffect(() => {
    if (!imageFile) {
      setImagePreviewUrl(null);
      return;
    }

    const url = URL.createObjectURL(imageFile);
    setImagePreviewUrl(url);
    return () => {
      URL.revokeObjectURL(url);
    };
  }, [imageFile]);

  useEffect(() => {
    if (imageFile || uploadedImageUrl) setShowScreenshot(true);
  }, [imageFile, uploadedImageUrl]);

  function setThemeAndPersist(next: "light" | "dark") {
    setTheme(next);
    document.documentElement.classList.toggle("dark", next === "dark");
    try {
      localStorage.setItem("theme", next);
    } catch {}
  }

  async function copyToClipboard(textToCopy: string) {
    try {
      await navigator.clipboard.writeText(textToCopy);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = textToCopy;
      ta.style.position = "fixed";
      ta.style.left = "-10000px";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
  }

  async function onAnalyze() {
    setError(null);
    setResult(null);
    setIsLoading(true);

    try {
      let image_url: string | undefined = uploadedImageUrl ?? undefined;

      if (!image_url && imageFile) {
        setIsUploading(true);
        const uploaded = await uploadToCloudinary(imageFile);
        image_url = uploaded.secureUrl;
        setUploadedImageUrl(uploaded.secureUrl);
      }

      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, image_url }),
      });

      const data = (await res.json()) as unknown;
      if (!res.ok) {
        const message =
          typeof (data as { error?: unknown })?.error === "string"
            ? ((data as { error: string }).error as string)
            : "Request failed";
        setError(message);
        return;
      }

      setResult(data as AnalyzeResponse);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Network error");
    } finally {
      setIsLoading(false);
      setIsUploading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-40 left-1/2 h-[520px] w-[980px] -translate-x-1/2 rounded-full bg-gradient-to-r from-indigo-500/12 via-sky-500/10 to-emerald-500/10 blur-3xl" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(148,163,184,0.16)_1px,transparent_0)] [background-size:24px_24px]" />
      </div>

      <main className="mx-auto w-full max-w-6xl px-5 py-10 sm:px-6">
        <header className="flex flex-col gap-5">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-2xl border border-border bg-card shadow-sm">
                <span className="text-lg font-semibold">S</span>
              </div>
              <div>
                <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Scam Detection AI</h1>
                <p className="mt-0.5 text-sm text-muted-foreground">
                  Paste a message or add a screenshot. Get an instant, multi-agent risk breakdown.
                </p>
              </div>
            </div>

            <button
              type="button"
              className="inline-flex h-10 items-center gap-2 rounded-full border border-border bg-card px-4 text-sm font-medium shadow-sm hover:bg-muted"
              onClick={() => {
                const next = (theme ?? "light") === "dark" ? "light" : "dark";
                setThemeAndPersist(next);
              }}
              aria-label="Toggle theme"
            >
              <span className="text-xs text-muted-foreground">Theme</span>
              <span className="font-semibold">{theme === "dark" ? "Dark" : "Light"}</span>
            </button>
          </div>

          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="text-sm font-semibold">Quick start</div>
                <div className="mt-1 text-sm text-muted-foreground">
                  Try a realistic example, then tweak it.
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {[
                  "Your bank account will be suspended today. Verify now: https://bit.ly/verify-acc",
                  "Hi, this is the delivery agent. Pay the customs fee using gift cards.",
                  "Can you share the OTP? I accidentally sent it to your number.",
                ].map((ex) => (
                  <button
                    key={ex}
                    type="button"
                    className="rounded-full border border-border bg-background px-3 py-1.5 text-xs text-foreground hover:bg-muted"
                    onClick={() => {
                      setText(ex);
                      setError(null);
                      setResult(null);
                    }}
                  >
                    Use example
                  </button>
                ))}
              </div>
            </div>
          </div>
        </header>

        <div className="mt-8 grid gap-6 md:grid-cols-2">
          <section className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-base font-semibold">Input</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Paste the full message. Include links, phone numbers, and payment instructions.
                </p>
              </div>
              <div className="text-xs text-muted-foreground">{text.length.toLocaleString()} chars</div>
            </div>

            <label className="sr-only" htmlFor="message">
              Message text
            </label>
            <textarea
              id="message"
              className="mt-4 min-h-[220px] w-full resize-y rounded-xl border border-border bg-background p-3 text-sm leading-6 shadow-sm"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Example: Your account will be suspended today. Verify immediately: https://..."
            />

            <div className="mt-4">
              <button
                type="button"
                className="inline-flex items-center gap-2 text-sm font-medium text-foreground hover:underline"
                onClick={() => setShowScreenshot((v) => !v)}
              >
                {showScreenshot ? "Hide" : "Add"} screenshot
                <span className="text-xs text-muted-foreground">(optional)</span>
              </button>

              {showScreenshot ? (
                <div className="mt-3 rounded-xl border border-border bg-background p-3">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <div className="text-sm font-medium">Screenshot</div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Drag & drop an image (PNG/JPEG), or click to select. We upload to Cloudinary before analysis.
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {uploadedImageUrl ? (
                        <a
                          className="text-xs text-sky-600 underline hover:text-sky-700 dark:text-sky-400"
                          href={uploadedImageUrl}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Uploaded link
                        </a>
                      ) : null}
                      {(imageFile || uploadedImageUrl) ? (
                        <button
                          type="button"
                          className="h-9 rounded-full border border-border bg-card px-4 text-xs font-medium hover:bg-muted"
                          onClick={() => {
                            setImageFile(null);
                            setUploadedImageUrl(null);
                            if (fileInputRef.current) fileInputRef.current.value = "";
                          }}
                          disabled={isLoading || isUploading}
                        >
                          Remove
                        </button>
                      ) : null}
                    </div>
                  </div>

                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/png,image/jpeg,image/jpg"
                    className="sr-only"
                    disabled={isLoading || isUploading}
                    onChange={(e) => {
                      const f = e.target.files?.[0] ?? null;
                      setImageFile(f);
                      setUploadedImageUrl(null);
                    }}
                  />

                  <div
                    className="mt-3 flex min-h-[132px] cursor-pointer items-center justify-center rounded-xl border border-dashed border-border bg-muted px-4 text-center text-sm text-muted-foreground hover:bg-muted/80"
                    role="button"
                    tabIndex={0}
                    onClick={() => fileInputRef.current?.click()}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
                    }}
                    onDragOver={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                    }}
                    onDrop={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      const f = e.dataTransfer.files?.[0] ?? null;
                      if (!f) return;
                      if (!/^image\/(png|jpe?g)$/i.test(f.type)) {
                        setError("Please drop a PNG or JPEG image.");
                        return;
                      }
                      setError(null);
                      setImageFile(f);
                      setUploadedImageUrl(null);
                    }}
                    aria-label="Upload screenshot"
                  >
                    {imagePreviewUrl ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={imagePreviewUrl}
                        alt="Selected screenshot preview"
                        className="max-h-[180px] w-auto rounded-lg border border-border object-contain shadow-sm"
                      />
                    ) : uploadedImageUrl ? (
                      <div>
                        Screenshot already uploaded.
                        <div className="mt-1 text-xs">Click “Remove” to change it.</div>
                      </div>
                    ) : (
                      <div>
                        <div className="font-medium text-foreground">Drop image here</div>
                        <div className="mt-1 text-xs">or click to browse</div>
                      </div>
                    )}
                  </div>
                </div>
              ) : null}
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                type="button"
                className="inline-flex h-10 items-center justify-center gap-2 rounded-full bg-foreground px-5 text-sm font-medium text-background shadow-sm transition hover:opacity-95 disabled:opacity-50"
                onClick={onAnalyze}
                disabled={!canAnalyze}
              >
                {isUploading ? "Uploading…" : isLoading ? "Analyzing…" : "Analyze"}
              </button>
              <button
                type="button"
                className="h-10 rounded-full border border-border bg-card px-5 text-sm font-medium text-foreground shadow-sm hover:bg-muted disabled:opacity-50"
                onClick={() => {
                  setText("");
                  setImageFile(null);
                  setUploadedImageUrl(null);
                  setShowScreenshot(false);
                  setResult(null);
                  setError(null);
                }}
                disabled={isLoading}
              >
                Clear
              </button>
              <div className="text-xs text-muted-foreground" aria-live="polite">
                {isUploading ? "Uploading image…" : isLoading ? "Analyzing…" : ""}
              </div>
            </div>

            {error ? (
              <div
                className="mt-4 rounded-xl border border-red-500/25 bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-300"
                role="alert"
              >
                {error}
              </div>
            ) : null}
          </section>

          <section className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-base font-semibold">Results</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  You’ll see an overall risk rating plus what each agent noticed.
                </p>
              </div>
              {result ? (
                <span
                  className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${labelBadge(
                    result.overall.label
                  )}`}
                >
                  {formatLabel(result.overall.label)}
                </span>
              ) : null}
            </div>

            {!result && !isLoading ? (
              <div className="mt-6 rounded-xl border border-border bg-background p-4 text-sm text-muted-foreground">
                Paste a message (and optionally add a screenshot), then click Analyze.
              </div>
            ) : null}

            {isLoading && !result ? (
              <div className="mt-6 space-y-3">
                <div className="h-4 w-44 rounded bg-muted" />
                <div className="h-2 w-full rounded bg-muted" />
                <div className="h-28 w-full rounded-xl bg-muted" />
              </div>
            ) : null}

            {result ? (
              <div className="mt-6 space-y-6">
                <div className="rounded-2xl border border-border bg-background p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-sm font-medium">Overall risk</div>
                    <div className="text-sm text-muted-foreground">
                      <span className="font-semibold text-foreground">{result.overall.score}/100</span>
                    </div>
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    Confidence: <span className="font-medium text-foreground">{result.overall.confidence}</span>
                  </div>
                  <div className="mt-3 h-2 w-full rounded-full bg-muted">
                    <div
                      className={`h-2 rounded-full ${labelBar(result.overall.label)}`}
                      style={{ width: `${Math.max(0, Math.min(100, result.overall.score))}%` }}
                    />
                  </div>
                  <p className="mt-3 text-sm text-foreground/90">{result.overall.summary}</p>
                  <div className="mt-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-sm font-medium">Recommendations</div>
                      <button
                        type="button"
                        className="h-9 rounded-full border border-border bg-card px-4 text-xs font-medium hover:bg-muted"
                        onClick={() =>
                          copyToClipboard(
                            [
                              `Label: ${formatLabel(result.overall.label)}`,
                              `Score: ${result.overall.score}/100 (${result.overall.confidence} confidence)`,
                              `Summary: ${result.overall.summary}`,
                              "Recommendations:",
                              ...result.overall.recommendations.map((r) => `- ${r}`),
                            ].join("\n")
                          )
                        }
                      >
                        Copy
                      </button>
                    </div>
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-foreground/90">
                      {result.overall.recommendations.map((r) => (
                        <li key={r}>{r}</li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="text-sm font-semibold">Agent reports</div>
                  <div className="grid gap-3">
                    {result.agents.map((a) => (
                      <details key={a.name} className="group rounded-2xl border border-border bg-background p-4">
                        <summary className="cursor-pointer list-none select-none">
                          <div className="flex flex-wrap items-baseline justify-between gap-2">
                            <div className="text-sm font-semibold">{a.name}</div>
                            <div className="text-xs text-muted-foreground">{a.focus}</div>
                          </div>
                          <div className="mt-2 text-xs text-muted-foreground group-open:hidden">
                            Click to expand
                          </div>
                        </summary>
                        <p className="mt-3 text-sm text-foreground/90">{a.finding}</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {a.signals.map((s) => (
                            <span
                              key={s}
                              className="rounded-full border border-border bg-card px-3 py-1 text-xs text-foreground/90"
                            >
                              {s}
                            </span>
                          ))}
                        </div>
                      </details>
                    ))}
                  </div>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted-foreground">
                  <div>Request ID: {result.requestId}</div>
                  <button
                    type="button"
                    className="h-9 rounded-full border border-border bg-card px-4 text-xs font-medium hover:bg-muted"
                    onClick={() => copyToClipboard(result.requestId)}
                  >
                    Copy request ID
                  </button>
                </div>
              </div>
            ) : null}
          </section>
        </div>

        <footer className="mt-10 text-xs text-muted-foreground">
          Tip: Even if the score is low, never share OTPs, passwords, or recovery codes.
        </footer>
      </main>
    </div>
  );
}
