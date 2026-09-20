"use client";

import { useEffect, useState } from "react";

export function useCanUseLiveCamera(): boolean {
  const [canUse, setCanUse] = useState<boolean>(false);

  useEffect((): void => {
    setCanUse(
      window.isSecureContext && Boolean(navigator.mediaDevices?.getUserMedia),
    );
  }, []);

  return canUse;
}
