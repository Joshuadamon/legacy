import { BottomSheetModal, BottomSheetView } from "@gorhom/bottom-sheet";
import { useRouter } from "expo-router";
import { useMemo, useRef, useState } from "react";
import { Text, View } from "react-native";

import { ApiError, api } from "../src/api";
import { useAuth } from "../src/auth-context";
import { GhostButton, PrimaryButton, Screen, Toast, hapticError } from "../src/components/game-ui";
import { colors, fonts, makeStyles } from "../src/theme";

const useStyles = makeStyles((palette) => ({
  scroll: { flex: 1, paddingHorizontal: 24, paddingTop: 24 },
  kicker: {
    color: palette.textMuted,
    fontFamily: fonts.uiMedium,
    letterSpacing: 1.4,
    fontSize: 12,
    borderTopWidth: 1,
    borderTopColor: palette.gold,
    paddingTop: 12,
  },
  title: { color: palette.text, fontFamily: fonts.display, fontSize: 34, marginTop: 8, marginBottom: 12 },
  note: { color: palette.textMuted, fontFamily: fonts.body, fontSize: 16, lineHeight: 24, marginBottom: 20 },
  sheet: { paddingHorizontal: 22, paddingBottom: 28 },
  sheetTitle: { color: palette.text, fontFamily: fonts.display, fontSize: 28, marginBottom: 8 },
}));

export default function SettingsScreen() {
  const styles = useStyles();
  const router = useRouter();
  const { signOut } = useAuth();
  const sheet = useRef<BottomSheetModal>(null);
  const snaps = useMemo(() => ["46%"], []);
  const [step, setStep] = useState<1 | 2>(1);
  const [toast, setToast] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function openDelete() {
    setStep(1);
    setToast(null);
    sheet.current?.present();
  }

  async function handleSignOut() {
    setBusy(true);
    setToast(null);
    try {
      await signOut();
      router.replace("/age");
    } catch {
      void hapticError();
      setToast("The sign out did not finish.");
    } finally {
      setBusy(false);
    }
  }

  async function removeAccount() {
    setBusy(true);
    setToast(null);
    try {
      await api("/api/account/delete", { method: "POST" });
      sheet.current?.dismiss();
      await signOut();
      router.replace("/age");
    } catch (error) {
      void hapticError();
      setToast(error instanceof ApiError ? error.message : "The account stayed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen testID="settings-screen">
      <View style={styles.scroll}>
        <Text style={styles.kicker}>SETTINGS</Text>
        <Text style={styles.title}>The record</Text>
        <Text style={styles.note}>
          Deleting an account closes the user, the sessions, the profile, and the saves. On the web, support requests
          go to anvilandember@thelittlebrownphamily.com.
        </Text>
        <Toast message={toast} />
        <GhostButton
          testID="sign-out-button"
          label={busy ? "Signing out..." : "Sign out"}
          disabled={busy}
          onPress={() => void handleSignOut()}
        />
        <View style={{ height: 12 }} />
        <GhostButton testID="delete-account-button" label="Delete account" tone="danger" onPress={openDelete} />
        <View style={{ height: 12 }} />
        <GhostButton testID="settings-back-button" label="Back" onPress={() => router.back()} />
      </View>
      <BottomSheetModal
        ref={sheet}
        snapPoints={snaps}
        onDismiss={() => setStep(1)}
        backgroundStyle={{ backgroundColor: colors.surfaceRaised }}
        handleIndicatorStyle={{ backgroundColor: colors.gold }}
      >
        <BottomSheetView style={styles.sheet} testID="delete-account-sheet">
          {step === 1 ? (
            <View testID="delete-step-one">
              <Text style={styles.sheetTitle}>Delete the account?</Text>
              <Text style={styles.note}>This is the first confirmation. The record is still here.</Text>
              <PrimaryButton testID="continue-delete-button" label="Continue" tone="danger" onPress={() => setStep(2)} />
              <View style={{ height: 12 }} />
              <GhostButton testID="cancel-delete-account" label="Cancel" onPress={() => sheet.current?.dismiss()} />
            </View>
          ) : (
            <View testID="delete-step-two">
              <Text style={styles.sheetTitle}>Close it for good?</Text>
              <Text style={styles.note}>The second confirmation soft-deletes the account. Old tokens stop working.</Text>
              <PrimaryButton
                testID="confirm-delete-account"
                label={busy ? "Closing..." : "Delete account"}
                disabled={busy}
                tone="danger"
                onPress={() => void removeAccount()}
              />
              <View style={{ height: 12 }} />
              <GhostButton testID="cancel-delete-account" label="Cancel" onPress={() => sheet.current?.dismiss()} />
            </View>
          )}
        </BottomSheetView>
      </BottomSheetModal>
    </Screen>
  );
}
