import { useRouter } from "expo-router";
import { useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";

import { ApiError } from "../src/api";
import { PrimaryButton, Screen, Toast } from "../src/components/game-ui";
import { colors, fonts, makeStyles } from "../src/theme";
import { useBackgrounds, useNewGame } from "../src/use-game";

const useStyles = makeStyles((palette) => ({
  scroll: { paddingHorizontal: 24, paddingBottom: 32 },
  kicker: {
    color: palette.accent,
    fontFamily: fonts.uiMedium,
    letterSpacing: 1.4,
    fontSize: 12,
    marginTop: 18,
  },
  title: {
    color: palette.text,
    fontFamily: fonts.display,
    fontSize: 34,
    marginTop: 8,
    marginBottom: 8,
  },
  lede: {
    color: palette.textMuted,
    fontFamily: fonts.body,
    fontSize: 16,
    marginBottom: 20,
  },
  input: {
    borderColor: palette.line,
    borderWidth: 1,
    borderRadius: 8,
    color: palette.text,
    fontFamily: fonts.ui,
    fontSize: 18,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginBottom: 18,
    backgroundColor: palette.surface,
  },
  card: {
    borderColor: palette.line,
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    backgroundColor: palette.surface,
  },
  cardOn: { borderColor: palette.accent },
  cardTitle: { color: palette.text, fontFamily: fonts.uiMedium, fontSize: 17 },
  cardBody: { color: palette.textMuted, fontFamily: fonts.body, fontSize: 15, marginTop: 4 },
}));

export default function CreateScreen() {
  const styles = useStyles();
  const router = useRouter();
  const backgrounds = useBackgrounds();
  const create = useNewGame();
  const [name, setName] = useState("");
  const [key, setKey] = useState("stable");
  const [toast, setToast] = useState<string | null>(null);

  async function begin() {
    if (!name.trim()) {
      setToast("A life needs a name.");
      return;
    }
    setToast(null);
    try {
      await create.mutateAsync({ name: name.trim(), background_key: key });
      router.replace("/game");
    } catch (error) {
      setToast(error instanceof ApiError ? error.message : "The birth did not take.");
    }
  }

  return (
    <Screen testID="create-screen">
      <KeyboardAwareScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <Text style={styles.kicker}>BIRTH</Text>
        <Text style={styles.title}>Where you start</Text>
        <Text style={styles.lede}>The house you are born into sets the first numbers. It does not set the ending.</Text>
        <Toast message={toast} />
        <TextInput
          testID="character-name-input"
          value={name}
          onChangeText={setName}
          placeholder="Name"
          placeholderTextColor={colors.textFaint}
          autoCapitalize="words"
          style={styles.input}
        />
        {(backgrounds.data?.backgrounds ?? []).map((item) => {
          const selected = item.key === key;
          return (
            <Pressable
              key={item.key}
              testID={`background-${item.key}`}
              accessibilityRole="button"
              accessibilityState={{ selected }}
              onPress={() => setKey(item.key)}
              style={[styles.card, selected ? styles.cardOn : null]}
            >
              <Text style={styles.cardTitle}>{item.label}</Text>
              <Text style={styles.cardBody}>{item.blurb}</Text>
            </Pressable>
          );
        })}
        <View style={{ height: 12 }} />
        <PrimaryButton
          testID="begin-legacy-button"
          label={create.isPending ? "Beginning..." : "Begin legacy"}
          disabled={create.isPending}
          onPress={() => void begin()}
        />
      </KeyboardAwareScrollView>
    </Screen>
  );
}
