import { NextResponse } from "next/server";
import crypto from "crypto";

export const runtime = "nodejs";

type SignRequest = {
  folder?: string;
};

export async function POST(req: Request) {
  let body: SignRequest = {};
  try {
    body = (await req.json()) as SignRequest;
  } catch {
    body = {};
  }

  const folder = typeof body.folder === "string" ? body.folder : undefined;

  const cloudName = process.env.CLOUDINARY_CLOUD_NAME;
  const apiKey = process.env.CLOUDINARY_API_KEY;
  const apiSecret = process.env.CLOUDINARY_API_SECRET;

  if (!cloudName || !apiKey || !apiSecret) {
    return NextResponse.json(
      { error: "Missing Cloudinary env vars" },
      { status: 500 }
    );
  }

  const timestamp = Math.floor(Date.now() / 1000);

  // Cloudinary signature: sha1("folder=...&timestamp=..." + api_secret)
  const params: string[] = [];
  if (folder) params.push(`folder=${folder}`);
  params.push(`timestamp=${timestamp}`);

  const toSign = params.join("&");
  const signature = crypto
    .createHash("sha1")
    .update(toSign + apiSecret)
    .digest("hex");

  return NextResponse.json({
    cloudName,
    apiKey,
    timestamp,
    signature,
    folder: folder ?? null,
  });
}
