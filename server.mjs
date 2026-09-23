import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("./web/", import.meta.url));
const port = Number(process.env.PORT || 3000);
const mimeTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".svg": "image/svg+xml",
};

function resolveAsset(urlPath) {
  const relativePath = normalize(decodeURIComponent(urlPath)).replace(/^(\.\.[/\\])+/, "");
  const candidate = join(root, relativePath === "/" ? "index.html" : relativePath);
  if (!candidate.startsWith(root) || !existsSync(candidate) || !statSync(candidate).isFile()) {
    return join(root, "index.html");
  }
  return candidate;
}

createServer((request, response) => {
  const asset = resolveAsset(new URL(request.url || "/", "http://localhost").pathname);
  response.writeHead(200, {
    "Content-Type": mimeTypes[extname(asset)] || "application/octet-stream",
    "Cache-Control": asset.endsWith("index.html") ? "no-cache" : "public, max-age=3600",
    "X-Content-Type-Options": "nosniff",
  });
  createReadStream(asset).pipe(response);
}).listen(port, "0.0.0.0", () => {
  console.log(`QuorumFlow live lab listening on port ${port}`);
});
