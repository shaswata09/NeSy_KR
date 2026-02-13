import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  defaultStaticDatasetId,
  fetchApiDatasets,
  staticDatasets,
} from "../data/index.js";

const GlobalStateContext = createContext(null);

// Apply data-theme attribute synchronously so CSS vars resolve before children render
function applyTheme(t) {
  const root = document.documentElement;
  if (t === "dark") {
    root.setAttribute("data-theme", "dark");
  } else {
    root.removeAttribute("data-theme");
  }
}

const PAGE_SIZE = 50;

export function StateProvider({ children }) {
  // Theme: 'light' | 'dark'
  const [theme, setTheme] = useState(() => {
    let initial = "light";
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("nesy-theme");
      if (stored === "dark" || stored === "light") {
        initial = stored;
      } else if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
        initial = "dark";
      }
      applyTheme(initial);
    }
    return initial;
  });

  const toggleTheme = useCallback(() => {
    setTheme((prev) => {
      const next = prev === "dark" ? "light" : "dark";
      localStorage.setItem("nesy-theme", next);
      applyTheme(next);
      return next;
    });
  }, []);

  // Available datasets (static + dynamically discovered API datasets)
  const [availableDatasets, setAvailableDatasets] = useState(staticDatasets);
  const [datasetsReady, setDatasetsReady] = useState(false);

  // Fetch API datasets from the unified server
  const refreshApiDatasets = useCallback(() => {
    fetchApiDatasets().then((apiDs) => {
      setAvailableDatasets([...staticDatasets, ...apiDs]);
      if (!datasetsReady) setDatasetsReady(true);
    });
  }, [datasetsReady]);

  // Auto-fetch on mount
  useEffect(() => {
    refreshApiDatasets();
  }, [refreshApiDatasets]);

  // Dataset selection
  const [activeDatasetId, setActiveDatasetId] = useState(
    () => localStorage.getItem("nesy-dataset") ?? defaultStaticDatasetId,
  );
  const [activeSplit, setActiveSplit] = useState("all");
  const [dataset, setDataset] = useState([]);
  const [datasetLoading, setDatasetLoading] = useState(true);

  // Pagination (only used for type:'api' datasets)
  const [pageOffset, setPageOffset] = useState(0);
  const [totalItems, setTotalItems] = useState(0);
  const [isPaginated, setIsPaginated] = useState(false);

  // Image selection
  const [selectedImageId, setSelectedImageId] = useState(null);

  // Re-resolve activeDatasetId once API datasets arrive
  // (e.g. if localStorage had 'api:gqa' from a previous session)
  const resolvedInitial = useRef(false);
  useEffect(() => {
    if (!datasetsReady || resolvedInitial.current) return;
    resolvedInitial.current = true;
    const stored = localStorage.getItem("nesy-dataset");
    if (stored && availableDatasets.some((d) => d.id === stored)) {
      setActiveDatasetId(stored);
    } else if (availableDatasets.length > 0) {
      setActiveDatasetId(availableDatasets[0].id);
    }
  }, [datasetsReady, availableDatasets]);

  // Load dataset when activeDatasetId or availableDatasets change
  useEffect(() => {
    if (!datasetsReady) return;
    let cancelled = false;
    const entry = availableDatasets.find((d) => d.id === activeDatasetId);
    if (!entry) {
      setDataset([]);
      setDatasetLoading(false);
      setIsPaginated(false);
      return;
    }

    setDatasetLoading(true);

    if (entry.type === "api") {
      setIsPaginated(true);
      setPageOffset(0);

      // Default to "all" but if dataset has splits and current split isn't in it, reset
      const defaultSplit = entry.splits?.includes(activeSplit)
        ? activeSplit
        : "all";
      if (defaultSplit !== activeSplit) {
        setActiveSplit(defaultSplit);
        return; // Effect will re-run with new split
      }

      entry
        .loadPage(0, PAGE_SIZE, activeSplit)
        .then((res) => {
          if (cancelled) return;
          setDataset(res.items);
          setTotalItems(res.total);
          setPageOffset(res.offset);
          setSelectedImageId(res.items[0]?.id ?? null);
          setDatasetLoading(false);
        })
        .catch((err) => {
          if (cancelled) return;
          console.error("Failed to load API dataset:", err);
          setDataset([]);
          setTotalItems(0);
          setDatasetLoading(false);
        });
    } else {
      setIsPaginated(false);
      setTotalItems(0);
      setPageOffset(0);
      entry.load().then((data) => {
        if (cancelled) return;
        setDataset(data);
        setSelectedImageId(data[0]?.id ?? null);
        setDatasetLoading(false);
      });
    }

    return () => {
      cancelled = true;
    };
  }, [activeDatasetId, activeSplit, datasetsReady, availableDatasets]);

  // Load a specific page (API datasets only)
  const loadPage = useCallback(
    (offset) => {
      const entry = availableDatasets.find((d) => d.id === activeDatasetId);
      if (!entry || entry.type !== "api") return;

      setDatasetLoading(true);
      entry
        .loadPage(offset, PAGE_SIZE, activeSplit)
        .then((res) => {
          setDataset(res.items);
          setTotalItems(res.total);
          setPageOffset(res.offset);
          setSelectedImageId(res.items[0]?.id ?? null);
          setDatasetLoading(false);
        })
        .catch((err) => {
          console.error("Failed to load page:", err);
          setDatasetLoading(false);
        });
    },
    [activeDatasetId, availableDatasets, activeSplit],
  );

  const nextPage = useCallback(() => {
    const next = pageOffset + PAGE_SIZE;
    if (next < totalItems) loadPage(next);
  }, [pageOffset, totalItems, loadPage]);

  const prevPage = useCallback(() => {
    const prev = Math.max(0, pageOffset - PAGE_SIZE);
    if (pageOffset > 0) loadPage(prev);
  }, [pageOffset, loadPage]);

  const switchDataset = useCallback((id) => {
    localStorage.setItem("nesy-dataset", id);
    setActiveDatasetId(id);
  }, []);

  // Entity interaction
  const [selectedEntityId, setSelectedEntityId] = useState(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState(null);
  const [hoveredEntityId, setHoveredEntityId] = useState(null);

  const selectedImage = dataset.find((d) => d.id === selectedImageId) ?? null;

  const value = {
    // Theme
    theme,
    toggleTheme,

    // Dataset switching
    availableDatasets,
    activeDatasetId,
    activeSplit,
    setActiveSplit,
    switchDataset,
    refreshApiDatasets,
    datasetLoading,

    // Dataset
    dataset,
    selectedImageId,
    setSelectedImageId,
    selectedImage,

    // Pagination
    isPaginated,
    pageOffset,
    pageSize: PAGE_SIZE,
    totalItems,
    nextPage,
    prevPage,

    // Entity
    selectedEntityId,
    setSelectedEntityId,
    selectedEdgeId,
    setSelectedEdgeId,
    hoveredEntityId,
    setHoveredEntityId,
  };

  return (
    <GlobalStateContext.Provider value={value}>
      {children}
    </GlobalStateContext.Provider>
  );
}

export function useGlobalState() {
  const ctx = useContext(GlobalStateContext);
  if (!ctx)
    throw new Error("useGlobalState must be used within a StateProvider");
  return ctx;
}
