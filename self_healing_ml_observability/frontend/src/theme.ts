import { extendTheme, ThemeConfig } from "@chakra-ui/react";

const config: ThemeConfig = {
  initialColorMode: "dark",
  useSystemColorMode: false,
};

export const theme = extendTheme({
  config,
  fonts: {
    heading: "Inter, Geist Sans, Segoe UI, sans-serif",
    body: "Inter, Geist Sans, Segoe UI, sans-serif",
  },
  layerStyles: {
    glassPanel: {
      bg: "rgba(255, 255, 255, 0.03)",
      backdropFilter: "blur(20px)",
      border: "1px solid",
      borderColor: "rgba(255, 255, 255, 0.08)",
      borderRadius: "xl",
    },
  },
  styles: {
    global: {
      body: {
        bg: "#121721",
        color: "#E6EDF3",
        backgroundImage: "radial-gradient(circle at 30% 20%, #121721 0%, #080A0F 72%)",
        fontWeight: 300,
      },
    },
  },
  colors: {
    aegis: {
      50: "#ebf8ff",
      500: "#3182CE",
      600: "#2B6CB0",
      700: "#2C5282",
      900: "#1A365D",
    },
  },
});
