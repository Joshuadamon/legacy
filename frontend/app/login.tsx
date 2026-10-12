import { useState } from "react";
import { Text, TextInput, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";

import { ApiError } from "../src/api";
import { useAuth } from "../src/auth-context";
import { GhostButton, PrimaryButton, Screen, Toast } from "../src/components/game-ui";
import { colors, fonts, makeStyles } from "../src/theme";

const useStyles = makeStyles((colors) => ({
  scroll: { flexGrow: 1, justifyContent: "center", paddingHorizontal: 24, paddingVertical: 32 },
  word: {
    color: colors.gold,
    fontFamily: fonts.display,
    fontSize: 42,
    letterSpacing: 6,
  },
  rule: {
    width: 48,
    height: 1,
    backgroundColor: colors.gold,
    marginTop: 14,
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
  const { signIn, register, loginEmail, linkEmail } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
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

  async function registerWithEmail() {
    if (!name.trim() || !email.trim() || password.length < 8) {
      setToast("A name, an email, and a password of 8 characters open the record.");
      return;
    }
    setBusy(true);
    setToast(null);
    try {
      await register(name.trim(), email.trim(), password);
    } catch (error) {
      setToast(error instanceof ApiError ? error.message : "The account did not open.");
    } finally {
      setBusy(false);
    }
  }

  async function loginWithEmail() {
    if (!email.trim() || !password) {
      setToast("The email and password are both needed.");
      return;
    }
    setBusy(true);
    setToast(null);
    try {
      await loginEmail(email.trim(), password);
    } catch (error) {
      setToast(error instanceof ApiError ? error.message : "The email did not match.");
    } finally {
      setBusy(false);
    }
  }

  async function linkWithEmail() {
    if (!email.trim() || password.length < 8) {
      setToast("Linking needs an email and a password of 8 characters.");
      return;
    }
    setBusy(true);
    setToast(null);
    try {
      await linkEmail(email.trim(), password);
      setToast("The email is on this account.");
    } catch (error) {
      setToast(error instanceof ApiError ? error.message : "The email did not attach.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen testID="login-screen">
      <KeyboardAwareScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <Text style={styles.word}>LEGACY</Text>
        <View style={styles.rule} />
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
        <Text style={styles.line}>Or use an email on the same account.</Text>
        <TextInput
          testID="email-input"
          value={email}
          onChangeText={setEmail}
          placeholder="Email"
          placeholderTextColor={colors.textFaint}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="email-address"
          style={styles.input}
        />
        <TextInput
          testID="password-input"
          value={password}
          onChangeText={setPassword}
          placeholder="Password"
          placeholderTextColor={colors.textFaint}
          secureTextEntry
          style={styles.input}
        />
        <GhostButton
          testID="register-email-button"
          label={busy ? "Opening..." : "Register with email"}
          disabled={busy}
          onPress={() => void registerWithEmail()}
        />
        <View style={{ height: 12 }} />
        <GhostButton testID="login-email-button" label="Log in with email" disabled={busy} onPress={() => void loginWithEmail()} />
        <View style={{ height: 12 }} />
        <GhostButton testID="link-email-button" label="Link email to this session" disabled={busy} onPress={() => void linkWithEmail()} />
        <View />
      </KeyboardAwareScrollView>
    </Screen>
  );
}
