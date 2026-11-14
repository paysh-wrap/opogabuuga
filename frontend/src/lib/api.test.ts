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

test("structured error details become readable text instead of a bare HTTP code", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({ detail: { errors: ["no EVAL accounts — Fast Evaluation applies to EVAL accounts only"], warnings: [] } }), { status: 422 }));
  await expect(api("/api/z")).rejects.toEqual(new ApiError(422, "no EVAL accounts — Fast Evaluation applies to EVAL accounts only"));
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({ detail: [{ msg: "Field required" }, { msg: "Input should be a valid integer" }] }), { status: 422 }));
  await expect(api("/api/z")).rejects.toEqual(new ApiError(422, "Field required; Input should be a valid integer"));
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response("{}", { status: 500 }));
  await expect(api("/api/z")).rejects.toEqual(new ApiError(500, "HTTP 500"));
});
