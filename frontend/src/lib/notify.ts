// Browser notifications (§18 Settings → notifications). Opt-in per browser, permission-gated; no push services.
const KEY = "pt_browser_notify";

export function notifySupported(): boolean {
  return typeof window !== "undefined" && "Notification" in window;
}

export function browserNotifyEnabled(): boolean {
  try {
    return notifySupported() && localStorage.getItem(KEY) === "1" && Notification.permission === "granted";
  } catch {
    return false;
  }
}

/** Asks the browser for permission (user gesture) and stores the opt-in only when granted. */
export async function enableBrowserNotify(): Promise<NotificationPermission | "unsupported"> {
  if (!notifySupported()) return "unsupported";
  const p = Notification.permission === "granted" ? "granted" : await Notification.requestPermission();
  try {
    if (p === "granted") localStorage.setItem(KEY, "1");
  } catch {
    /* storage blocked: stays off */
  }
  return p;
}

export function disableBrowserNotify(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* nothing stored */
  }
}

export function browserNotify(title: string, body: string): boolean {
  if (!browserNotifyEnabled()) return false;
  new Notification(`Paytience · ${title}`, { body, tag: `pt-${title}` });
  return true;
}
