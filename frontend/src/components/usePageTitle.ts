import { useEffect } from "react";

export function usePageTitle(page: string): void {
  useEffect(() => {
    document.title = `Paytience · ${page}`;
  }, [page]);
}
