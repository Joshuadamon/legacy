import { useRouter } from "expo-router";
import { useState } from "react";
import { Text, TextInput, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";

import { ApiError } from "../src/api";
import { GhostButton, PrimaryButton, Screen, Toast } from "../src/components/game-ui";
import { colors, fonts, makeStyles } from "../src/theme";
import { useContinueHeir, useGameState, useHeirs } from "../src/use-game";

const useStyles = makeStyles((palette) => ({
  scroll: { paddingHorizontal: 24, paddingBottom: 36 },
  kicker: {
    color: palette.accent,
    fontFamily: fonts.uiMedium,
    letterSpacing: 1.4,
    fontSize: 12,
    marginTop: 18,
  },
  title: { color: palette.text, fontFamily: fonts.display, fontSize: 34, marginVertical: 8 },
  obituary: { color: palette.text, fontFamily: fonts.body, fontSize: 17, lineHeight: 26, marginBottom: 16 },
  earned: { color: palette.accent, fontFamily: fonts.uiMedium, fontSize: 18, marginBottom: 6 },
  balance: { color: palette.textMuted, fontFamily: fonts.ui, fontSize: 15, marginBottom: 20 },
  input: {
    borderColor: palette.line,
    borderWidth: 1,
    borderRadius: 8,
    color: palette.text,
    backgroundColor: palette.surface,
    fontFamily: fonts.ui,
    fontSize: 18,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginBottom: 10,
  },
  gap: { height: 10 },
}));

export default function HeirScreen() {
  const styles = useStyles();
  const router = useRouter();
  const state = useGameState();
  const dead = state.data?.save?.alive === false;
  const heirs = useHeirs(dead);
  const continueHeir = useContinueHeir();
  const [name, setName] = useState("");
  const [toast, setToast] = useState<string | null>(null);

  async function choose(heirId: string, heirName?: string) {
    setToast(null);
    try {
      await continueHeir.mutateAsync({ heir_id: heirId, name: heirName });
      router.replace("/game");
    } catch (error) {
      setToast(error instanceof ApiError ? error.message : "The line did not continue.");
    }
  }

  return (
    <Screen testID="heir-screen">
      <KeyboardAwareScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <Text style={styles.kicker}>DEATH</Text>
        <Text style={styles.title}>The record closes</Text>
        <Toast message={toast} />
        <Text testID="obituary" style={styles.obituary}>
          {heirs.data?.obituary ?? "The obituary is still being set in type."}
        </Text>
        <Text testID="marks-earned" style={styles.earned}>
          You earned {heirs.data?.marks_earned ?? state.data?.save?.marks_earned ?? 0} Legacy Marks.
        </Text>
        <Text style={styles.balance}>Balance {heirs.data?.marks_balance ?? "—"}</Text>
        {(heirs.data?.heirs ?? [])
          .filter((heir) => heir.kind === "child")
          .map((heir) => (
            <View key={heir.id} style={styles.gap}>
              <GhostButton
                testID={`continue-${heir.id}`}
                label={`Continue as ${heir.name}, ${heir.age_now}`}
                disabled={continueHeir.isPending}
                onPress={() => void choose(heir.id)}
              />
            </View>
          ))}
        <View style={styles.gap} />
        <TextInput
          testID="heir-new-name"
          value={name}
          onChangeText={setName}
          placeholder="Name a distant relative"
          placeholderTextColor={colors.textFaint}
          style={styles.input}
        />
        <PrimaryButton
          testID="continue-new-button"
          label="Continue as a distant relative"
          disabled={continueHeir.isPending}
          onPress={() => void choose("new", name.trim() || undefined)}
        />
      </KeyboardAwareScrollView>
    </Screen>
  );
}
