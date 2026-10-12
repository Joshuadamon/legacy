import { useMemo } from "react";
import { StyleSheet } from "react-native";

export const colors = {
  background: "#0E0E10",
  surface: "#17171B",
  surfaceRaised: "#1F1F24",
  text: "#F2EDE4",
  textMuted: "#8A8578",
  textFaint: "#8A8578",
  accent: "#C9A227",
  danger: "#C0392B",
  line: "#2A2A30",
  border: "#2A2A30",
  good: "#6B8E4E",
  ember: "#FF6B1A",
  emberDeep: "#B33C0A",
  gold: "#C9A227",
  blood: "#8E1B1B",
  success: "#6B8E4E",
  bone: "#8A8578",
  moon: "#B8BCC4",
} as const;

export const fonts = {
  display: "Literata_600SemiBold",
  body: "SourceSans3_400Regular",
  ui: "SourceSans3_400Regular",
  uiMedium: "SourceSans3_600SemiBold",
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
} as const;

export const radius = {
  sm: 6,
  md: 12,
  lg: 20,
} as const;

export function useTheme() {
  return { colors, fonts, spacing, radius };
}

export function makeStyles<T extends StyleSheet.NamedStyles<T>>(
  factory: (palette: typeof colors) => T,
) {
  return function useStyles() {
    const { colors: palette } = useTheme();
    return useMemo(() => StyleSheet.create(factory(palette)), [palette]);
  };
}
