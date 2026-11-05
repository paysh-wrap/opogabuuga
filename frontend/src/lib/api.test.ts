import { api, ApiError } from "./api";

afterEach(() => vi.restoreAllMocks());

test("mutations send the CSRF cookie value as header; GETs do not", async () => {
  document.cookie = "pt_csrf=tok123";
  const f = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response("{}", { status: 200 }));
  await api("/api/x", { method: "PUT", body: "{}" });
  await api("/api/y");
  const put = f.mock.calls[0]![1]!.headers as Headers;
  const get = f.mock.calls[1]![1]!.headers as Headers;
  expect(put.get("x-csrf-token")).toBe("tok123");
  expect(get.get("x-csrf-token")).toBeNull();
});

test("errors surface server detail (no silent failures)", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response('{"detail":"Key rejected"}', { status: 422 }));
  await expect(api("/api/z")).rejects.toEqual(new ApiError(422, "Key rejected"));
});
