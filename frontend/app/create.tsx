import { Redirect, useRouter } from "expo-router";
import { useState } from "react";
import { Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";

import { ApiError } from "../src/api";
import { useAuth } from "../src/auth-context";
import { PrimaryButton, Screen, Toast } from "../src/components/game-ui";
import { colors, fonts, makeStyles } from "../src/theme";
import { useBackgrounds, useNewGame, useProfile } from "../src/use-game";

const useStyles = makeStyles((palette) => ({
  scroll: { paddingHorizontal: 24, paddingBottom: 32 },
  kicker: {
    color: palette.textMuted,
    fontFamily: fonts.uiMedium,
    letterSpacing: 1.4,
    fontSize: 12,
    marginTop: 18,
    borderTopWidth: 1,
    borderTopColor: palette.gold,
    paddingTop: 12,
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
  cardOn: { borderColor: palette.gold },
  cardTitle: { color: palette.text, fontFamily: fonts.display, fontSize: 20 },
  cardBody: { color: palette.textMuted, fontFamily: fonts.body, fontSize: 15, marginTop: 4 },
  chips: { flexDirection: "row", gap: 8, paddingVertical: 4 },
  chip: {
    borderColor: palette.line,
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 8,
    backgroundColor: palette.surface,
  },
  chipOn: { borderColor: palette.gold, backgroundColor: palette.surfaceRaised },
  chipText: { color: palette.text, fontFamily: fonts.ui, fontSize: 15 },
  chipTextOn: { color: palette.gold },
}));

export default function CreateScreen() {
  const styles = useStyles();
  const router = useRouter();
  const { user } = useAuth();
  const backgrounds = useBackgrounds();
  const profile = useProfile();
  const create = useNewGame();
  const [name, setName] = useState("");
  const [key, setKey] = useState("stable");
  const [species, setSpecies] = useState<"human" | "vampire" | "lycanthrope" | "witch">("human");
  const [clan, setClan] = useState("");
  const [subtype, setSubtype] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  const held = profile.data?.profile.unlocks.species ?? [];
  const holdsThirst = held.includes("vampire");
  const holdsMoon = held.includes("lycanthrope");
  const holdsCraft = held.includes("witch");
  const clans = backgrounds.data?.vampire_clans ?? [];
  const subtypes = backgrounds.data?.lycan_subtypes ?? [];
  const chosenClan = clan || clans[0] || "";
  const chosenSubtype = subtype || subtypes[0] || "";
  const birthChoices = [
    { id: "human" as const, label: "Human" },
    ...(holdsThirst ? [{ id: "vampire" as const, label: "Vampire" }] : []),
    ...(holdsMoon ? [{ id: "lycanthrope" as const, label: "Lycanthrope" }] : []),
    ...(holdsCraft ? [{ id: "witch" as const, label: "Witch" }] : []),
  ];

  async function begin() {
    if (!name.trim()) {
      setToast("A life needs a name.");
      return;
    }
    setToast(null);
    try {
      const birth = birthChoices.some((item) => item.id === species) ? species : "human";
      await create.mutateAsync({
        name: name.trim(),
        background_key: key,
        species: birth,
        clan: birth === "vampire" ? chosenClan : undefined,
        subtype: birth === "lycanthrope" ? chosenSubtype : undefined,
      });
      router.replace("/game");
    } catch (error) {
      setToast(error instanceof ApiError ? error.message : "The birth did not take.");
    }
  }

  if (!user?.age_confirmed) return <Redirect href="/age" />;

  return (
    <Screen testID="create-screen">
      <KeyboardAwareScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <Text style={styles.kicker}>BIRTH</Text>
        <Text style={styles.title}>Where you start</Text>
        <Text style={styles.lede}>The house you are born into sets the first numbers. It does not set the ending.</Text>
        <Toast message={toast} />
        {birthChoices.length > 1 ? (
          <>
            <Text style={styles.kicker}>BLOOD</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
              {birthChoices.map((item) => {
                const selected = species === item.id;
                return (
                  <Pressable
                    key={item.id}
                    testID={`birth-species-${item.id}`}
                    accessibilityRole="button"
                    accessibilityState={{ selected }}
                    onPress={() => setSpecies(item.id)}
                    style={[styles.chip, selected ? styles.chipOn : null]}
                  >
                    <Text style={[styles.chipText, selected ? styles.chipTextOn : null]}>{item.label}</Text>
                  </Pressable>
                );
              })}
            </ScrollView>
            {species === "vampire" ? (
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
                {clans.map((item) => {
                  const selected = item === chosenClan;
                  const slug = item.toLowerCase().replace(/\s+/g, "-");
                  return (
                    <Pressable
                      key={item}
                      testID={`birth-clan-${slug}`}
                      accessibilityRole="button"
                      accessibilityState={{ selected }}
                      onPress={() => setClan(item)}
                      style={[styles.chip, selected ? styles.chipOn : null]}
                    >
                      <Text style={[styles.chipText, selected ? styles.chipTextOn : null]}>{item}</Text>
                    </Pressable>
                  );
                })}
              </ScrollView>
            ) : null}
            {species === "lycanthrope" ? (
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
                {subtypes.map((item) => {
                  const selected = item === chosenSubtype;
                  return (
                    <Pressable
                      key={item}
                      testID={`birth-subtype-${item}`}
                      accessibilityRole="button"
                      accessibilityState={{ selected }}
                      onPress={() => setSubtype(item)}
                      style={[styles.chip, selected ? styles.chipOn : null]}
                    >
                      <Text style={[styles.chipText, selected ? styles.chipTextOn : null]}>{item}</Text>
                    </Pressable>
                  );
                })}
              </ScrollView>
            ) : null}
          </>
        ) : null}
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
