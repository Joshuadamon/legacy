import { Image } from "expo-image";
import { useState } from "react";
import { Text, TextInput, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";

import { ApiError } from "../src/api";
import { useAuth } from "../src/auth-context";
import { PrimaryButton, Screen, Toast } from "../src/components/game-ui";
import { colors, fonts, makeStyles } from "../src/theme";

const useStyles = makeStyles((colors) => ({
  scroll: { flexGrow: 1, justifyContent: "center", paddingHorizontal: 24, paddingVertical: 32 },
  mark: { width: 72, height: 72, marginBottom: 20 },
  word: {
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 42,
    letterSpacing: 6,
  },
  line: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 18,
    marginTop: 8,
    marginBottom: 28,
  },
  input: {
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 8,
    color: colors.text,
    fontFamily: fonts.ui,
    fontSize: 18,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginBottom: 16,
    backgroundColor: colors.surface,
  },
}));

export default function LoginScreen() {
  const styles = useStyles();
  const { signIn } = useAuth();
  const [name, setName] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function begin() {
    const trimmed = name.trim();
    if (!trimmed) {
      setToast("A life needs a name.");
      return;
    }
    setBusy(true);
    setToast(null);
    try {
      await signIn(trimmed);
    } catch (error) {
      setToast(error instanceof ApiError ? error.message : "Sign-in did not hold.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen testID="login-screen">
      <KeyboardAwareScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <Image source={require("../assets/icon.png")} style={styles.mark} contentFit="contain" />
        <Text style={styles.word}>LEGACY</Text>
        <Text style={styles.line}>One life. Then the next.</Text>
        <Toast message={toast} />
        <TextInput
          testID="session-name-input"
          value={name}
          onChangeText={setName}
          placeholder="Your name"
          placeholderTextColor={colors.textFaint}
          autoCapitalize="words"
          style={styles.input}
        />
        <PrimaryButton testID="begin-session-button" label={busy ? "Opening..." : "Begin"} disabled={busy} onPress={() => void begin()} />
        <View />
      </KeyboardAwareScrollView>
    </Screen>
  );
}
