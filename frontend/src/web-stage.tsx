import { type ReactNode } from "react";
import { Platform, StyleSheet, View, type ViewStyle } from "react-native";

import { colors } from "./theme";

const keyArt = require("../assets/legacy-main-screen.jpg") as { uri?: string } | string;

/**
 * Web gets the full viewport width because phone-width constraints clipped tabs and text on desktop.
 * Native path stays unwrapped.
 */
export function WebStage({ children }: { children: ReactNode }) {
  if (Platform.OS !== "web") return <>{children}</>;
  const uri = typeof keyArt === "string" ? keyArt : keyArt?.uri || "";
  return (
    <View style={styles.stage}>
      <View style={[styles.art, uri ? webArt(uri) : null]} />
      <View style={styles.column}>{children}</View>
    </View>
  );
}

function webArt(uri: string): ViewStyle {
  return {
    backgroundImage: `url("${uri}")`,
    backgroundSize: "cover",
    backgroundPosition: "center",
    backgroundRepeat: "no-repeat",
  } as ViewStyle;
}

const styles = StyleSheet.create({
  stage: {
    flex: 1,
    minHeight: "100%",
    backgroundColor: colors.background,
    alignItems: "center",
  },
  art: {
    position: "absolute",
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    opacity: 0.22,
  },
  column: {
    flex: 1,
    width: "100%",
    backgroundColor: colors.background,
  },
});
