import { extendTheme, type ThemeConfig } from "@chakra-ui/react";

const config: ThemeConfig = {
  initialColorMode: "dark",
  useSystemColorMode: false,
};

const theme = extendTheme({
  config,

  fonts: {
    heading: `'JetBrains Mono', monospace`,
    body: `'JetBrains Mono', monospace`,
    mono: `'JetBrains Mono', monospace`,
  },

  colors: {
    aegis: {
      black: "#050505",
      bg: "#0A0A0A",
      border: "#2D3748",
      lime: "#CCFF00",
      limeDim: "rgba(204,255,0,0.15)",
      orange: "#FF4D00",
      orangeDim: "rgba(255,77,0,0.15)",
      red: "#FF0033",
      text: "#E0E0E0",
      textDim: "rgba(224,224,224,0.4)",
      green: "#00FF41",
    },
  },

  radii: {
    none: "0",
    sm: "0",
    base: "0",
    md: "0",
    lg: "0",
    xl: "0",
    "2xl": "0",
    "3xl": "0",
    full: "0",
  },

  styles: {
    global: {
      "html, body": {
        bg: "#050505",
        color: "#E0E0E0",
        fontFamily: `'JetBrains Mono', monospace`,
        fontSize: "13px",
        lineHeight: 1.5,
        overflowX: "hidden",
      },
      "*": {
        borderRadius: "0 !important",
      },
      "::-webkit-scrollbar": {
        width: "4px",
        height: "4px",
      },
      "::-webkit-scrollbar-track": {
        bg: "#050505",
      },
      "::-webkit-scrollbar-thumb": {
        bg: "#2D3748",
      },
      /* CRT glitch keyframes */
      "@keyframes crtGlitch": {
        "0%, 100%": { transform: "translate(0)" },
        "20%": { transform: "translate(-2px, 1px)" },
        "40%": { transform: "translate(2px, -1px)" },
        "60%": { transform: "translate(-1px, 2px)" },
        "80%": { transform: "translate(1px, -2px)" },
      },
      "@keyframes scanline": {
        "0%": { top: "-2px" },
        "100%": { top: "100%" },
      },
      "@keyframes blink": {
        "0%, 100%": { opacity: 1 },
        "50%": { opacity: 0 },
      },
      "@keyframes scanSweep": {
        "0%": { transform: "translateX(-100%)", opacity: 0.8 },
        "50%": { opacity: 1 },
        "100%": { transform: "translateX(100%)", opacity: 0 },
      },
    },
  },

  components: {
    Button: {
      baseStyle: {
        borderRadius: "0",
        fontFamily: `'JetBrains Mono', monospace`,
        fontWeight: 600,
        textTransform: "uppercase",
        letterSpacing: "0.1em",
        fontSize: "xs",
      },
    },
    Badge: {
      baseStyle: {
        borderRadius: "0",
        fontFamily: `'JetBrains Mono', monospace`,
        textTransform: "uppercase",
        letterSpacing: "0.15em",
        fontSize: "0.55rem",
      },
    },
    Table: {
      baseStyle: {
        th: {
          fontFamily: `'JetBrains Mono', monospace`,
          textTransform: "uppercase",
          letterSpacing: "0.12em",
          fontSize: "0.6rem",
          borderColor: "#2D3748",
        },
        td: {
          fontFamily: `'JetBrains Mono', monospace`,
          fontSize: "0.7rem",
          borderColor: "#2D3748",
        },
      },
    },
    Progress: {
      baseStyle: {
        track: {
          borderRadius: "0",
          bg: "rgba(204,255,0,0.08)",
        },
        filledTrack: {
          borderRadius: "0",
        },
      },
    },
    Input: {
      baseStyle: {
        field: {
          borderRadius: "0",
          fontFamily: `'JetBrains Mono', monospace`,
        },
      },
    },
    Stat: {
      baseStyle: {
        label: {
          fontFamily: `'JetBrains Mono', monospace`,
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          fontSize: "0.55rem",
          color: "aegis.textDim",
        },
        number: {
          fontFamily: `'JetBrains Mono', monospace`,
          fontWeight: 700,
        },
      },
    },
  },
});

export default theme;
