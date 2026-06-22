const http = require("http");

const IPTV_HOST = "lionzsmt.com";
const IPTV_PORT = 8080;

exports.handler = async (event) => {
  const qs = event.queryStringParameters || {};
  const reqPath = qs.path || "/player_api.php";

  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(qs)) {
    if (k !== "path") {
      params.append(k, v);
    }
  }

  const queryString = params.toString();
  const fullPath = queryString ? reqPath + "?" + queryString : reqPath;

  return new Promise((resolve) => {
    const options = {
      hostname: IPTV_HOST,
      port: IPTV_PORT,
      path: fullPath,
      method: "GET",
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
      },
    };

    const req = http.request(options, (res) => {
      const chunks = [];
      res.on("data", (chunk) => chunks.push(chunk));
      res.on("end", () => {
        const body = Buffer.concat(chunks).toString("utf-8");
        resolve({
          statusCode: res.statusCode,
          headers: {
            "Content-Type": res.headers["content-type"] || "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
          },
          body,
        });
      });
    });

    req.on("error", (err) => {
      resolve({
        statusCode: 502,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
        body: JSON.stringify({ error: err.message }),
      });
    });

    req.end();
  });
};
