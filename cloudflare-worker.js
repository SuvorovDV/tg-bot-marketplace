// Cloudflare Worker: прозрачный прокси к api.telegram.org.
// Деплой: https://dash.cloudflare.com → Workers & Pages → Create Worker → вставить этот код.

export default {
  async fetch(request) {
    const url = new URL(request.url);
    url.host = "api.telegram.org";
    url.protocol = "https:";
    url.port = "";
    const proxied = new Request(url, request);
    proxied.headers.set("Host", "api.telegram.org");
    return fetch(proxied);
  },
};
