export async function uploadToCloudinary(file: File, folder = "scamshield") {
  const signRes = await fetch("/api/cloudinary-sign", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ folder }),
  });

  if (!signRes.ok) {
    const t = await signRes.text().catch(() => "");
    throw new Error(`Failed to get Cloudinary signature: ${t.slice(0, 200)}`);
  }

  const { cloudName, apiKey, timestamp, signature } = (await signRes.json()) as {
    cloudName: string;
    apiKey: string;
    timestamp: number;
    signature: string;
  };

  const form = new FormData();
  form.append("file", file);
  form.append("api_key", apiKey);
  form.append("timestamp", String(timestamp));
  form.append("signature", signature);
  form.append("folder", folder);

  const uploadRes = await fetch(
    `https://api.cloudinary.com/v1_1/${cloudName}/image/upload`,
    { method: "POST", body: form }
  );

  if (!uploadRes.ok) {
    const t = await uploadRes.text().catch(() => "");
    throw new Error(`Cloudinary upload failed: ${t.slice(0, 300)}`);
  }

  const data = (await uploadRes.json()) as {
    secure_url: string;
    public_id: string;
  };

  return {
    secureUrl: data.secure_url,
    publicId: data.public_id,
  };
}
