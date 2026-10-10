import * as Haptics from "expo-haptics";
import { type ReactNode } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { fonts, makeStyles } from "../theme";

const useStyles = makeStyles((colors) => ({
  screen: {
    flex: 1,
    backgroundColor: colors.background,
  },
  button: {
    backgroundColor: colors.accent,
    borderRadius: 8,
    paddingVertical: 14,
    paddingHorizontal: 16,
    alignItems: "center",
  },
  buttonText: {
    color: colors.background,
    fontFamily: fonts.uiMedium,
    fontSize: 16,
    lineHeight: 22,
    letterSpacing: 0.3,
    textAlign: "center",
  },
  ghost: {
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 8,
    paddingVertical: 14,
    paddingHorizontal: 16,
  },
  fill: {
    flexGrow: 1,
    flexShrink: 1,
    flexBasis: 0,
  },
  ghostText: {
    color: colors.text,
    fontFamily: fonts.ui,
    fontSize: 16,
  },
  disabled: { opacity: 0.45 },
  meterLabel: {
    color: colors.textMuted,
    fontFamily: fonts.uiMedium,
    fontSize: 12,
    letterSpacing: 0.6,
    textTransform: "uppercase",
  },
  track: {
    height: 4,
    backgroundColor: colors.line,
    borderRadius: 2,
    marginTop: 6,
    overflow: "hidden",
  },
  meterFill: {
    height: 4,
    backgroundColor: colors.accent,
  },
  statRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.line,
  },
  statLabel: {
    color: colors.textMuted,
    fontFamily: fonts.ui,
    fontSize: 15,
  },
  statValue: {
    color: colors.text,
    fontFamily: fonts.uiMedium,
    fontSize: 15,
  },
  toast: {
    backgroundColor: colors.surfaceRaised,
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
    marginBottom: 12,
  },
  toastText: {
    color: colors.text,
    fontFamily: fonts.ui,
    fontSize: 15,
  },
}));

export async function hapticTap() {
  try {
    await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
  } catch {
    // Web and desktop have no haptic motor.
  }
}

export async function hapticSuccess() {
  try {
    await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
  } catch {
    // Web and desktop have no haptic motor.
  }
}

export async function hapticError() {
  try {
    await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
  } catch {
    // Web and desktop have no haptic motor.
  }
}

export function Screen({ children, testID }: { children: ReactNode; testID?: string }) {
  const styles = useStyles();
  const insets = useSafeAreaInsets();
  return (
    <View testID={testID} style={[styles.screen, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
      {children}
    </View>
  );
}

export function PrimaryButton({
  label,
  onPress,
  testID,
  disabled,
}: {
  label: string;
  onPress: () => void;
  testID: string;
  disabled?: boolean;
}) {
  const styles = useStyles();
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      disabled={disabled}
      onPress={() => {
        void hapticTap();
        onPress();
      }}
      style={[styles.button, disabled ? styles.disabled : null]}
    >
      <Text style={styles.buttonText}>{label}</Text>
    </Pressable>
  );
}

export function GhostButton({
  label,
  onPress,
  testID,
  disabled,
  fill,
}: {
  label: string;
  onPress: () => void;
  testID: string;
  disabled?: boolean;
  fill?: boolean;
}) {
  const styles = useStyles();
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      disabled={disabled}
      onPress={() => {
        void hapticTap();
        onPress();
      }}
      style={[styles.ghost, fill ? styles.fill : null, disabled ? styles.disabled : null]}
    >
      <Text style={styles.ghostText}>{label}</Text>
    </Pressable>
  );
}

export function Meter({ label, value }: { label: string; value: number }) {
  const styles = useStyles();
  const width = `${Math.max(0, Math.min(100, value))}%` as const;
  return (
    <View>
      <Text style={styles.meterLabel}>
        {label} {Math.round(value)}
      </Text>
      <View style={styles.track}>
        <View style={[styles.meterFill, { width }]} />
      </View>
    </View>
  );
}

export function StatLine({ label, value }: { label: string; value: string | number }) {
  const styles = useStyles();
  return (
    <View style={styles.statRow}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={styles.statValue}>{value}</Text>
    </View>
  );
}

export function Toast({ message }: { message: string | null }) {
  const styles = useStyles();
  if (!message) return null;
  return (
    <View testID="toast" style={styles.toast}>
      <Text style={styles.toastText}>{message}</Text>
    </View>
  );
}

export function moneyLabel(value: number): string {
  const sign = value < 0 ? "-" : "";
  return `${sign}$${Math.abs(value).toLocaleString("en-US")}`;
}
