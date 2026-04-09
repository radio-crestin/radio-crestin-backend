interface Env {
  CDN_SIGNING_SECRET: string;
}

const ONE_MONTH = 60 * 60 * 24 * 30;

async function verifySignature(
  url: string,
  signature: string,
  secret: string
): Promise<boolean> {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, encoder.encode(url));
  const expected = Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  return expected === signature;
}

export default {
  async fetch(
    request: Request,
    env: Env,
    ctx: ExecutionContext
  ): Promise<Response> {
    const reqUrl = new URL(request.url);
    const imageUrl = reqUrl.searchParams.get("url");
    const signature = reqUrl.searchParams.get("sig");

    if (!imageUrl || !signature) {
      return new Response("Missing 'url' or 'sig' parameter", { status: 400 });
    }

    // Validate HMAC signature
    const valid = await verifySignature(imageUrl, signature, env.CDN_SIGNING_SECRET);
    if (!valid) {
      return new Response("Invalid signature", { status: 403 });
    }

    // Validate URL
    try {
      new URL(imageUrl);
    } catch {
      return new Response("Invalid URL", { status: 400 });
    }

    // Check edge cache
    const cache = caches.default;
    const cacheKey = new Request(reqUrl.toString(), { method: "GET" });
    const cached = await cache.match(cacheKey);
    if (cached) {
      return cached;
    }

    // Fetch from origin
    const originResponse = await fetch(imageUrl, {
      headers: { Accept: "image/*" },
    });

    if (!originResponse.ok) {
      return new Response("Image not found", {
        status: originResponse.status,
      });
    }

    const contentType =
      originResponse.headers.get("content-type") || "image/jpeg";

    const response = new Response(originResponse.body, {
      headers: {
        "Content-Type": contentType,
        "Cache-Control": `public, max-age=${ONE_MONTH}, s-maxage=${ONE_MONTH}, immutable`,
        "Access-Control-Allow-Origin": "*",
      },
    });

    // Cache at edge (non-blocking)
    ctx.waitUntil(cache.put(cacheKey, response.clone()));

    return response;
  },
};
