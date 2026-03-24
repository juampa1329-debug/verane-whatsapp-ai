import { useEffect, useState } from "react";

const MOBILE_BREAKPOINT = 980;
const TABLET_BREAKPOINT = 1280;

function getWidth() {
  if (typeof window === "undefined") return 1440;
  return window.innerWidth || 1440;
}

export default function useViewport() {
  const [width, setWidth] = useState(getWidth);

  useEffect(() => {
    const onResize = () => setWidth(getWidth());
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const isMobile = width <= MOBILE_BREAKPOINT;
  const isTablet = width > MOBILE_BREAKPOINT && width <= TABLET_BREAKPOINT;

  return {
    width,
    isMobile,
    isTablet,
    isCompact: width <= TABLET_BREAKPOINT,
  };
}
