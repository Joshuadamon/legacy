import { useRouter } from "expo-router";
import { useState } from "react";
import { Text, View } from "react-native";

import { api, ApiError } from "../src/api";
import { useAuth } from "../src/auth-context";
import { GhostButton, PrimaryButton, Screen, Toast } from "../src/components/game-ui";
import { fonts, makeStyles } from "../src/theme";

const useStyles = makeStyles((palette) => ({
  wrap: { flex: 1, justifyContent: "center", paddingHorizontal: 24 },
  kicker: {
    color: palette.accent,
    fontFamily: fonts.uiMedium,
    letterSpacing: 1.4,
    fontSize: 12,
  },
  title: { color: palette.text, fontFamily: fonts.display, fontSize: 34, marginTop: 8 },
  body: { color: palette.textMuted, fontFamily: fonts.body, fontSize: 18, lineHeight: 28, marginTop: 12, marginBottom: 24 },
  actions: { gap: 12 },
}));

export default function AgeScreen() {
  const styles = useStyles();
  const router = useRouter();
  const { status, confirmAge } = useAuth();
  const [blocked, setBlocked] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function older() {
    setToast(null);
    if (status !== "user") {
      router.replace("/login");
      return;
    }
    setBusy(true);
    try {
      await confirmAge();
      router.replace("/");
    } catch (error) {
      setToast(error instanceof ApiError ? error.message : "The confirmation did not hold.");
    } finally {
      setBusy(false);
    }
  }

  async function younger() {
    setToast(null);
    setBusy(true);
    try {
      await api("/api/auth/age", { method: "POST", body: JSON.stringify({ confirmed: false }) });
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 403) {
        setToast(error instanceof ApiError ? error.message : "The gate did not answer.");
        setBusy(false);
        return;
      }
    }
    setBusy(false);
    setBlocked(true);
  }

  if (blocked) {
    return (
      <Screen testID="age-blocked-screen">
        <View style={styles.wrap}>
          <Text style={styles.kicker}>LEGACY</Text>
          <Text style={styles.title}>Not yet.</Text>
          <Text style={styles.body}>This life sim is 17 or older. No account and no life were opened.</Text>
        </View>
      </Screen>
    );
  }

  return (
    <Screen testID="age-gate-screen">
      <View style={styles.wrap}>
        <Text style={styles.kicker}>LEGACY</Text>
        <Text style={styles.title}>Are you 17 or older?</Text>
        <Text style={styles.body}>LEGACY is a mature life sim, 17+. Are you 17 or older?</Text>
        <Toast message={toast} />
        <View style={styles.actions}>
          <PrimaryButton testID="age-yes-button" label={busy ? "One moment..." : "I am 17 or older"} disabled={busy} onPress={() => void older()} />
          <GhostButton testID="age-no-button" label="I am under 17" disabled={busy} onPress={() => void younger()} />
        </View>
      </View>
    </Screen>
  );
}
