import { useCallback, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useUiLayoutStore } from "../stores/uiLayoutStore";

const getRouteKey = (location) =>
  `${location.pathname}${location.search || ""}${location.hash || ""}`;

export function useGoBack({ fallbackPath = "/", replaceFallback = true } = {}) {
  const location = useLocation();
  const navigate = useNavigate();
  const getPreviousRoute = useUiLayoutStore((state) => state.getPreviousRoute);
  const isNavigatingRef = useRef(false);

  return useCallback(() => {
    if (isNavigatingRef.current) return;
    isNavigatingRef.current = true;

    const currentRoute = getRouteKey(location);
    const targetRoute = getPreviousRoute(currentRoute, fallbackPath);
    const shouldReplace = targetRoute === fallbackPath ? replaceFallback : true;

    navigate(targetRoute, { replace: shouldReplace });

    window.setTimeout(() => {
      isNavigatingRef.current = false;
    }, 250);
  }, [fallbackPath, getPreviousRoute, location, navigate, replaceFallback]);
}
