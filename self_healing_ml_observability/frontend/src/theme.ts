import { extendTheme, type ThemeConfig } from "@chakra-ui/react";

const config: ThemeConfig = {
  initialColorMode: "dark",
  useSystemColorMode: false,
};

const theme = extendTheme({
  config,

  fonts: {
    heading: `'Inter', 'JetBrains Mono', system-ui, sans-serif`,
    body: `'Inter', 'JetBrains Mono', system-ui, sans-serif`,
    mono: `'JetBrains Mono', 'SFMono-Regular', Consolas, monospace`,
  },

  colors: {
    aegis: {
      lime: "#9DFF3A",
      limeDim: "rgba(157,255,58,0.16)",
      orange: "#FF7A1A",
      orangeDim: "rgba(255,122,26,0.15)",
      red: "#FF3158",
      yellow: "#FFD166",
      green: "#14F195",
      cyan: "#38BDF8",
      violet: "#8B5CF6",
    },
  },

  semanticTokens: {
    colors: {
      "aegis.page": { default: "#F4F7FB", _dark: "#05070D" },
      "aegis.black": { default: "#FFFFFF", _dark: "#0B1020" },
      "aegis.bg": { default: "#F4F7FB", _dark: "#05070D" },
      "aegis.surface": { default: "#FFFFFF", _dark: "#0B1020" },
      "aegis.surfaceElevated": { default: "#F9FBFF", _dark: "#111827" },
      "aegis.border": { default: "#D8E0EA", _dark: "#243044" },
      "aegis.borderStrong": { default: "#AEBBD0", _dark: "#334155" },
      "aegis.text": { default: "#142033", _dark: "#E6EDF7" },
      "aegis.textMuted": { default: "#5E6B80", _dark: "#93A4B8" },
      "aegis.textFaint": { default: "#8492A6", _dark: "#64748B" },
      "aegis.textDim": { default: "#5E6B80", _dark: "#93A4B8" },
      "aegis.accent": { default: "#2563EB", _dark: "#9DFF3A" },
      "aegis.accentSoft": { default: "rgba(37,99,235,0.10)", _dark: "rgba(157,255,58,0.14)" },
      "aegis.warning": { default: "#D97706", _dark: "#FF7A1A" },
      "aegis.danger": { default: "#DC2626", _dark: "#FF3158" },
      "aegis.success": { default: "#059669", _dark: "#14F195" },
      "aegis.gridLine": { default: "rgba(37,99,235,0.09)", _dark: "rgba(157,255,58,0.055)" },
      "aegis.overlay": { default: "rgba(255,255,255,0.78)", _dark: "rgba(5,7,13,0.78)" },
    },
    shadows: {
      "aegis.card": { default: "0 18px 45px rgba(15,23,42,0.08)", _dark: "0 18px 50px rgba(0,0,0,0.38)" },
      "aegis.glow": { default: "0 0 0 rgba(37,99,235,0)", _dark: "0 0 28px rgba(157,255,58,0.12)" },
    },
  },

  radii: {
    sm: "0.5rem",
    base: "0.75rem",
    md: "1rem",
    lg: "1.25rem",
    xl: "1.5rem",
    "2xl": "1.75rem",
    full: "999px",
  },

  styles: {
    global: {
      "html, body, #root": {
        minHeight: "100%",
      },
      "html, body": {
        bg: "aegis.page",
        color: "aegis.text",
        fontSize: "14px",
        lineHeight: 1.6,
        overflowX: "hidden",
        scrollBehavior: "smooth",
        transition: "background-color 220ms ease, color 220ms ease",
      },
      "*, *::before, *::after": {
        boxSizing: "border-box",
      },
      "*:focus-visible": {
        outline: "3px solid",
        outlineColor: "aegis.accent",
        outlineOffset: "3px",
      },
      "::selection": {
        bg: "aegis.accentSoft",
        color: "aegis.text",
      },
      ".skip-link": {
        position: "absolute",
        left: "1rem",
        top: "-4rem",
        zIndex: 20,
        bg: "aegis.surface",
        color: "aegis.text",
        border: "1px solid",
        borderColor: "aegis.borderStrong",
        borderRadius: "full",
        px: 4,
        py: 2,
        transition: "top 160ms ease",
      },
      ".skip-link:focus": {
        top: "1rem",
      },
      "::-webkit-scrollbar": {
        width: "8px",
        height: "8px",
      },
      "::-webkit-scrollbar-track": {
        bg: "aegis.page",
      },
      "::-webkit-scrollbar-thumb": {
        bg: "aegis.borderStrong",
        borderRadius: "full",
      },
      "@media (prefers-reduced-motion: reduce)": {
        "*, *::before, *::after": {
          animationDuration: "0.01ms !important",
          animationIterationCount: "1 !important",
          scrollBehavior: "auto !important",
          transitionDuration: "0.01ms !important",
        },
      },
      "@keyframes crtGlitch": {
        "0%, 100%": { transform: "translate(0)" },
        "20%": { transform: "translate(-1px, 1px)" },
        "40%": { transform: "translate(1px, -1px)" },
        "60%": { transform: "translate(-1px, 1px)" },
        "80%": { transform: "translate(1px, -1px)" },
      },
      "@keyframes softPulse": {
        "0%, 100%": { opacity: 0.65, transform: "scale(1)" },
        "50%": { opacity: 1, transform: "scale(1.08)" },
      },
    },
  },

  components: {
    Button: {
      baseStyle: {
        borderRadius: "full",
        fontWeight: 700,
        letterSpacing: "0.04em",
        transition: "all 180ms ease",
      },
    },
    IconButton: {
      baseStyle: {
        borderRadius: "full",
        transition: "all 180ms ease",
      },
    },
    Badge: {
      baseStyle: {
        borderRadius: "full",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        fontSize: "0.62rem",
        px: 2,
        py: 0.5,
      },
    },
    Table: {
      baseStyle: {
        th: {
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          fontSize: "0.65rem",
          borderColor: "aegis.border",
          color: "aegis.textMuted",
        },
        td: {
          fontSize: "0.75rem",
          borderColor: "aegis.border",
          color: "aegis.text",
        },
      },
    },
    Progress: {
      baseStyle: {
        track: {
          borderRadius: "full",
          bg: "aegis.accentSoft",
        },
        filledTrack: {
          borderRadius: "full",
          transition: "width 0.6s ease-out",
        },
      },
    },
    Input: {
      baseStyle: {
        field: {
          borderRadius: "full",
          bg: "aegis.surfaceElevated",
          borderColor: "aegis.border",
          color: "aegis.text",
          _placeholder: { color: "aegis.textFaint" },
        },
      },
    },
    Stat: {
      baseStyle: {
        label: {
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          fontSize: "0.65rem",
          color: "aegis.textMuted",
        },
        number: {
          fontWeight: 800,
        },
      },
    },
  },
});

export default theme;
