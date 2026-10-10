import { useMemo } from "react";
import { StyleSheet } from "react-native";

export const colors = {
  background: "#0E0E10",
  surface: "#17171B",
  surfaceRaised: "#222228",
  text: "#F4F1EA",
  textMuted: "#A39E93",
  textFaint: "#6F6B63",
  accent: "#C6A15B",
  danger: "#B5524A",
  line: "#2C2C32",
  good: "#7D9A78",
} as const;

export const fonts = {
  display: "Literata_600SemiBold",
  body: "Literata_400Regular",
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
