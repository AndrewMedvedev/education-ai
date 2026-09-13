import { useEffect } from "react";
import { useLocation, useNavigationType } from "react-router-dom";
import { useUiLayoutStore } from "../stores/uiLayoutStore";

const getRouteKey = (location) =>
  `${location.pathname}${location.search || ""}${location.hash || ""}`;

export function useRouteHistoryTracker() {
  const location = useLocation();
  const navigationType = useNavigationType();
  const recordRoute = useUiLayoutStore((state) => state.recordRoute);

  useEffect(() => {
    recordRoute(getRouteKey(location), navigationType);
  }, [location, navigationType, recordRoute]);
}
