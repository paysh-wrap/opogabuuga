// Auto-reconnecting WebSocket (§2). Exponential backoff, keep-alive ping.
type Handler = (data: Record<string, unknown>) => void;

export class LiveSocket {
  private ws: WebSocket | null = null;
  private handlers = new Map<string, Set<Handler>>();
  private retry = 0;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private ping: ReturnType<typeof setInterval> | null = null;
  private stopped = false;
  onStatus: (up: boolean) => void = () => {};

  constructor(private url: string) {}

  start(): void {
    this.stopped = false;
    this.connect();
  }

  stop(): void {
    this.stopped = true;
    if (this.timer) clearTimeout(this.timer);
    if (this.ping) clearInterval(this.ping);
    this.ws?.close();
  }

  on(event: string, h: Handler): () => void {
    if (!this.handlers.has(event)) this.handlers.set(event, new Set());
    this.handlers.get(event)!.add(h);
    return () => this.handlers.get(event)?.delete(h);
  }

  private connect(): void {
    const ws = new WebSocket(this.url);
    this.ws = ws;
    ws.onopen = () => {
      this.retry = 0;
      this.onStatus(true);
      this.ping = setInterval(() => ws.readyState === 1 && ws.send("ping"), 25_000);
    };
    ws.onmessage = (m) => {
      try {
        const { event, data } = JSON.parse(String(m.data)) as { event: string; data: Record<string, unknown> };
        this.handlers.get(event)?.forEach((h) => h(data));
        this.handlers.get("*")?.forEach((h) => h({ event, ...data }));
      } catch {
        /* ignore malformed frames */
      }
    };
    ws.onclose = () => {
      this.onStatus(false);
      if (this.ping) clearInterval(this.ping);
      if (this.stopped) return;
      const delay = Math.min(30_000, 1000 * 2 ** this.retry++);
      this.timer = setTimeout(() => this.connect(), delay);
    };
  }
}

export function wsUrl(): string {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${location.host}/api/ws`;
}
