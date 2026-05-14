import { useCallback, useEffect, useRef } from "react";
import { useColorMode } from "@chakra-ui/react";

const THEME_STORAGE_KEY = "aegis-theme";
type StoredTheme = "light" | "dark";

function isStoredTheme(value: string | null): value is StoredTheme {
  return value === "light" || value === "dark";
}

export function usePersistentColorMode() {
  const { colorMode, setColorMode } = useColorMode();
  const hasLoadedPreference = useRef(false);

  useEffect(() => {
    if (hasLoadedPreference.current) {
      return;
    }

    hasLoadedPreference.current = true;
    try {
      const savedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
      if (isStoredTheme(savedTheme) && savedTheme !== colorMode) {
        setColorMode(savedTheme);
      }
    } catch (error) {
      console.warn("Theme preference could not be loaded.", error);
    }
  }, [colorMode, setColorMode]);

  useEffect(() => {
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, colorMode);
    } catch (error) {
      console.warn("Theme preference could not be saved.", error);
    }
  }, [colorMode]);

  const toggleColorMode = useCallback(() => {
    setColorMode(colorMode === "dark" ? "light" : "dark");
  }, [colorMode, setColorMode]);

  return {
    colorMode,
    isDarkMode: colorMode === "dark",
    toggleColorMode,
  };
}
