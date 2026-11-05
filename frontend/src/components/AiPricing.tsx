/** Static, cited price list (as of 2026-11-05). Claude stays the main TradingAgents source; these are alternates. */
const ROWS: { fam: string; route: string; model: string; inp: string; out: string; run: string; url: string; works: boolean }[] = [
  { fam: "Qwen", route: "Alibaba Model Studio (official, Singapore)", model: "qwen-flash", inp: "0.05", out: "0.40", run: "≈ $0.03", url: "https://www.alibabacloud.com/help/en/model-studio/model-pricing", works: true },
  { fam: "Qwen", route: "Alibaba Model Studio (official)", model: "qwen-plus", inp: "0.40", out: "1.20", run: "≈ $0.16", url: "https://www.alibabacloud.com/help/en/model-studio/model-pricing", works: true },
  { fam: "Qwen", route: "Alibaba Model Studio (official)", model: "qwen-max", inp: "1.60", out: "6.40", run: "≈ $0.67", url: "https://www.alibabacloud.com/help/en/model-studio/model-pricing", works: true },
  { fam: "Kimi", route: "Kimi platform (official)", model: "kimi-k2.6", inp: "0.95", out: "4.00", run: "≈ $0.41", url: "https://platform.kimi.ai/docs/pricing/chat", works: true },
  { fam: "Kimi", route: "Kimi platform (official)", model: "kimi-k3", inp: "3.00", out: "15.00", run: "≈ $1.35", url: "https://platform.kimi.ai/docs/pricing/chat", works: true },
  { fam: "Kimi", route: "OpenRouter (cheapest listed host)", model: "moonshotai/kimi-k2.6", inp: "0.39", out: "1.64", run: "≈ $0.17", url: "https://openrouter.ai/moonshotai/kimi-k2.6", works: false },
];

export default function AiPricing() {
  return (
    <section className="rounded-xl border border-border bg-card p-4 text-sm" data-testid="ai-pricing">
      <h2 className="font-semibold text-gold">Cheapest ways to get Kimi / Qwen (alternates — Claude is the main source)</h2>
      <p className="text-xs opacity-80">Prices per 1M tokens, as of 2026-11-05 (check the link before buying). "Per run" = one daily TradingAgents analysis, about 300k in / 30k out tokens.</p>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full text-xs"><thead><tr className="text-left text-gold"><th>Model</th><th>Route</th><th>$ in</th><th>$ out</th><th>Per run</th><th /></tr></thead>
          <tbody>
            {ROWS.map((r) => (
              <tr key={r.route + r.model} className="border-t border-border">
                <td className="py-1"><b>{r.fam}</b> {r.model}</td><td>{r.route}{r.works ? "" : " — not usable in the app yet"}</td>
                <td>{r.inp}</td><td>{r.out}</td><td className="text-gold">{r.run}</td>
                <td><a href={r.url} target="_blank" rel="noreferrer noopener">source ↗</a></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs opacity-80">Notes: no free credit is offered by either official API. Kimi K2 models close to new users from Oct 31, 2026 and retire by end of Dec 2026 — use K3 after that. OpenRouter isn't supported directly by TradingAgents.</p>
    </section>
  );
}
