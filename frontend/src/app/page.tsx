"use client";

import { useMemo, useState } from "react";
import { uploadToCloudinary } from "../lib/uploadToCloudinary";

type AnalyzeResponse = {
  requestId: string;
  overall: {
    label: "likely_scam" | "uncertain" | "likely_legit";
    score: number;
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
      return "bg-red-600 text-white";
    case "uncertain":
      return "bg-amber-500 text-white";
    case "likely_legit":
      return "bg-emerald-600 text-white";
    default:
      return "bg-zinc-700 text-white";
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
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  const canAnalyze = useMemo(
    () => (text.trim().length > 0 || !!imageFile || !!uploadedImageUrl) && !isLoading && !isUploading,
    [text, isLoading, isUploading, imageFile, uploadedImageUrl]
  );

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
      <main className="mx-auto w-full max-w-6xl px-6 py-10">
        <header className="flex flex-col gap-2">
          <h1 className="text-3xl font-semibold tracking-tight">Scam Detection AI</h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Multi-agent demo UI. Today this uses a mock Next.js API route; later you can connect it to a Python backend.
          </p>
        </header>

        <div className="mt-8 grid gap-6 md:grid-cols-2">
          <section className="rounded-xl border border-black/10 bg-background p-5 dark:border-white/15">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-base font-semibold">Input</h2>
                <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
                  Paste the full message. Include any links, phone numbers, and payment instructions.
                </p>
              </div>
              <div className="text-xs text-zinc-600 dark:text-zinc-400">
                {text.length.toLocaleString()} chars
              </div>
            </div>

            <label className="sr-only" htmlFor="message">
              Message text
            </label>
            <textarea
              id="message"
              className="mt-4 min-h-[240px] w-full resize-y rounded-lg border border-black/10 bg-background p-3 text-sm leading-6 outline-none focus:ring-2 focus:ring-black/10 dark:border-white/15 dark:focus:ring-white/15"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Example: Your account will be suspended today. Verify immediately: https://..."
            />

            <div className="mt-4">
              <div className="text-sm font-medium">Optional screenshot</div>
              <p className="mt-1 text-xs text-zinc-600 dark:text-zinc-400">
                Upload a screenshot (JPEG/PNG). It will be uploaded to Cloudinary and analyzed by the Python backend.
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-3">
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/jpg"
                  disabled={isLoading || isUploading}
                  onChange={(e) => {
                    const f = e.target.files?.[0] ?? null;
                    setImageFile(f);
                    setUploadedImageUrl(null);
                  }}
                />
                {uploadedImageUrl ? (
                  <a
                    className="text-xs text-blue-600 underline dark:text-blue-400"
                    href={uploadedImageUrl}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Uploaded image link
                  </a>
                ) : null}
              </div>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                type="button"
                className="h-10 rounded-full bg-foreground px-5 text-sm font-medium text-background disabled:opacity-50"
                onClick={onAnalyze}
                disabled={!canAnalyze}
              >
                {isLoading ? "Analyzing…" : "Analyze"}
              </button>
              <button
                type="button"
                className="h-10 rounded-full border border-black/10 px-5 text-sm font-medium text-foreground disabled:opacity-50 dark:border-white/15"
                onClick={() => {
                  setText("");
                  setImageFile(null);
                  setUploadedImageUrl(null);
                  setResult(null);
                  setError(null);
                }}
                disabled={isLoading}
              >
                Clear
              </button>
              <div className="text-xs text-zinc-600 dark:text-zinc-400">
                {isUploading ? "Uploading image…" : isLoading ? "Analyzing…" : ""}
              </div>
            </div>

            {error ? (
              <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-300">
                {error}
              </div>
            ) : null}
          </section>

          <section className="rounded-xl border border-black/10 bg-background p-5 dark:border-white/15">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-base font-semibold">Results</h2>
                <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
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
              <div className="mt-6 rounded-lg border border-black/10 p-4 text-sm text-zinc-600 dark:border-white/15 dark:text-zinc-400">
                Paste a message on the left and click Analyze.
              </div>
            ) : null}

            {isLoading && !result ? (
              <div className="mt-6 space-y-3">
                <div className="h-4 w-40 rounded bg-black/10 dark:bg-white/10" />
                <div className="h-2 w-full rounded bg-black/10 dark:bg-white/10" />
                <div className="h-24 w-full rounded bg-black/10 dark:bg-white/10" />
              </div>
            ) : null}

            {result ? (
              <div className="mt-6 space-y-6">
                <div className="rounded-lg border border-black/10 p-4 dark:border-white/15">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-sm font-medium">Overall risk</div>
                    <div className="text-sm text-zinc-600 dark:text-zinc-400">
                      <span className="font-semibold text-foreground">{result.overall.score}/100</span>
                    </div>
                  </div>
                  <div className="mt-3 h-2 w-full rounded-full bg-black/10 dark:bg-white/10">
                    <div
                      className={`h-2 rounded-full ${labelBar(result.overall.label)}`}
                      style={{ width: `${Math.max(0, Math.min(100, result.overall.score))}%` }}
                    />
                  </div>
                  <p className="mt-3 text-sm text-zinc-700 dark:text-zinc-300">
                    {result.overall.summary}
                  </p>
                  <div className="mt-4">
                    <div className="text-sm font-medium">Recommendations</div>
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-zinc-700 dark:text-zinc-300">
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
                      <div
                        key={a.name}
                        className="rounded-lg border border-black/10 p-4 dark:border-white/15"
                      >
                        <div className="flex flex-wrap items-baseline justify-between gap-2">
                          <div className="text-sm font-semibold">{a.name}</div>
                          <div className="text-xs text-zinc-600 dark:text-zinc-400">{a.focus}</div>
                        </div>
                        <p className="mt-2 text-sm text-zinc-700 dark:text-zinc-300">{a.finding}</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {a.signals.map((s) => (
                            <span
                              key={s}
                              className="rounded-full border border-black/10 px-3 py-1 text-xs text-zinc-700 dark:border-white/15 dark:text-zinc-300"
                            >
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="text-xs text-zinc-600 dark:text-zinc-400">
                  Request ID: {result.requestId}
                </div>
              </div>
            ) : null}
          </section>
        </div>

        <footer className="mt-10 text-xs text-zinc-600 dark:text-zinc-400">
          Tip: Even if the score is low, never share OTPs or passwords.
        </footer>
      </main>
    </div>
  );
}
