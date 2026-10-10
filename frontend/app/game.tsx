import { BottomSheetModal, BottomSheetScrollView } from "@gorhom/bottom-sheet";
import { useRouter } from "expo-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, View } from "react-native";

import { ApiError } from "../src/api";
import {
  GhostButton,
  Meter,
  PrimaryButton,
  Screen,
  StatLine,
  Toast,
  hapticError,
  moneyLabel,
} from "../src/components/game-ui";
import { colors, fonts, makeStyles } from "../src/theme";
import { useAbandon, useChoice, useGameState, useProfile, type Flags, type Save } from "../src/use-game";

const STAGE: Record<string, string> = {
  infant: "Infant",
  child: "Child",
  teen: "Teen",
  young_adult: "Young",
  adult: "Adult",
  elder: "Elder",
};

const FLAG_LABELS: { key: keyof Flags; label: string }[] = [
  { key: "morality", label: "Morality" },
  { key: "honesty", label: "Honesty" },
  { key: "discipline", label: "Discipline" },
  { key: "aggression", label: "Aggression" },
  { key: "addiction", label: "Addiction" },
  { key: "faith", label: "Faith" },
  { key: "nature", label: "Nature" },
  { key: "ambition", label: "Ambition" },
  { key: "charisma", label: "Charisma" },
  { key: "resilience", label: "Resilience" },
];

const useStyles = makeStyles((palette) => ({
  scroll: { paddingHorizontal: 22, paddingBottom: 24 },
  topRow: { flexDirection: "row", justifyContent: "space-between", marginTop: 12 },
  name: { color: palette.text, fontFamily: fonts.display, fontSize: 28 },
  money: { color: palette.accent, fontFamily: fonts.uiMedium, fontSize: 18, marginTop: 8 },
  meta: { color: palette.textMuted, fontFamily: fonts.ui, fontSize: 14, marginTop: 4, marginBottom: 16 },
  meters: { gap: 10, marginBottom: 18 },
  outcome: { color: palette.textMuted, fontFamily: fonts.body, fontSize: 15, marginBottom: 14 },
  title: { color: palette.text, fontFamily: fonts.display, fontSize: 26, marginBottom: 8 },
  narrative: { color: palette.text, fontFamily: fonts.body, fontSize: 17, lineHeight: 26, marginBottom: 18 },
  choices: { gap: 10 },
  bar: {
    flexDirection: "row",
    alignItems: "stretch",
    width: "100%",
    gap: 8,
    paddingHorizontal: 16,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: palette.line,
  },
  passing: {
    ...StyleSheetAbsolute,
    backgroundColor: palette.background,
    alignItems: "center",
    justifyContent: "center",
  },
  passingText: { color: palette.textMuted, fontFamily: fonts.body, fontSize: 18, marginTop: 12 },
  sheet: { paddingHorizontal: 22, paddingBottom: 28 },
  sheetTitle: { color: palette.text, fontFamily: fonts.display, fontSize: 28, marginBottom: 12 },
  section: {
    color: palette.accent,
    fontFamily: fonts.uiMedium,
    fontSize: 12,
    letterSpacing: 1.2,
    marginTop: 18,
    marginBottom: 6,
  },
  note: { color: palette.textMuted, fontFamily: fonts.body, fontSize: 15, marginTop: 6 },
}));

const StyleSheetAbsolute = { position: "absolute" as const, left: 0, right: 0, top: 0, bottom: 0 };

export default function GameScreen() {
  const styles = useStyles();
  const router = useRouter();
  const state = useGameState();
  const profile = useProfile();
  const choice = useChoice();
  const abandon = useAbandon();
  const lifeRef = useRef<BottomSheetModal>(null);
  const abandonRef = useRef<BottomSheetModal>(null);
  const snaps = useMemo(() => ["78%"], []);
  const [toast, setToast] = useState<string | null>(null);
  const save = state.data?.save;

  useEffect(() => {
    if (!state.isSuccess || state.isFetching) return;
    if (!save) router.replace("/create");
    else if (!save.alive) router.replace("/heir");
  }, [state.isSuccess, state.isFetching, save, router]);

  async function pick(index: number) {
    setToast(null);
    try {
      const result = await choice.mutateAsync(index);
      if (!result.save.alive) router.replace("/heir");
    } catch (error) {
      void hapticError();
      setToast(error instanceof ApiError ? error.message : "The year did not resolve.");
    }
  }

  async function closeRecord() {
    try {
      await abandon.mutateAsync();
      abandonRef.current?.dismiss();
      router.replace("/create");
    } catch (error) {
      void hapticError();
      setToast(error instanceof ApiError ? error.message : "The record stayed open.");
    }
  }

  if (state.isLoading || !save || !save.alive) {
    return (
      <Screen>
        <View style={styles.passing}>
          <ActivityIndicator color={colors.accent} />
        </View>
      </Screen>
    );
  }

  return (
    <Screen testID="game-screen">
      <ScrollView contentContainerStyle={styles.scroll}>
        <Header save={save} />
        <Toast message={toast} />
        <View style={styles.meters}>
          <Meter label="Health" value={save.character.stats.health} />
          <Meter label="Happiness" value={save.character.stats.happiness} />
          <Meter label="Smarts" value={save.character.stats.smarts} />
          <Meter label="Looks" value={save.character.stats.looks} />
        </View>
        {save.last_outcome ? <Text style={styles.outcome}>Last year. {save.last_outcome}</Text> : null}
        <Text style={styles.title}>{save.current_event?.title}</Text>
        <Text style={styles.narrative}>{save.current_event?.narrative}</Text>
        <View style={styles.choices}>
          {(save.current_event?.choices ?? []).map((item, index) => (
            <GhostButton
              key={`${item.label}-${index}`}
              testID={`choice-${index}`}
              label={item.label}
              disabled={choice.isPending}
              onPress={() => void pick(index)}
            />
          ))}
        </View>
      </ScrollView>
      <View style={styles.bar}>
        <GhostButton fill testID="open-life-sheet" label="Life" onPress={() => lifeRef.current?.present()} />
        <GhostButton fill testID="open-lineage-button" label="Family" onPress={() => router.push("/lineage")} />
        <GhostButton fill testID="open-store-button" label="Marks" onPress={() => router.push("/store")} />
      </View>
      {choice.isPending ? (
        <View testID="year-passing" style={styles.passing}>
          <ActivityIndicator color={colors.accent} />
          <Text style={styles.passingText}>A year passes...</Text>
        </View>
      ) : null}
      <BottomSheetModal
        ref={lifeRef}
        snapPoints={snaps}
        backgroundStyle={{ backgroundColor: colors.surface }}
        handleIndicatorStyle={{ backgroundColor: colors.accent }}
      >
        <BottomSheetScrollView contentContainerStyle={styles.sheet} testID="life-sheet">
          <Text style={styles.sheetTitle}>{save.character.name}</Text>
          <Text style={styles.note}>{save.character.background}</Text>
          <Text style={styles.section}>VITALS</Text>
          <StatLine label="Money" value={moneyLabel(save.character.stats.money)} />
          <StatLine label="Reputation" value={save.character.stats.reputation} />
          <StatLine label="Family" value={save.character.stats.family} />
          <Text style={styles.section}>FLAGS</Text>
          {FLAG_LABELS.map((flag) => (
            <StatLine key={flag.key} label={flag.label} value={save.character.flags[flag.key]} />
          ))}
          <Text style={styles.section}>CHILDREN</Text>
          {save.character.children.length === 0 ? <Text style={styles.note}>None yet.</Text> : null}
          {save.character.children.map((child) => (
            <StatLine key={child.id} label={child.name} value={`born at ${child.born_parent_age}`} />
          ))}
          <Text style={styles.section}>OPEN TO YOU</Text>
          <Text style={styles.note}>
            {profile.data?.profile.unlocks.careers.length
              ? `Fields: ${profile.data.profile.unlocks.careers.join(", ")}`
              : "No career field is unlocked."}
          </Text>
          <Text style={styles.note}>
            {profile.data?.profile.unlocks.cosmetics.length
              ? `Keepsakes: ${profile.data.profile.unlocks.cosmetics.join(", ")}`
              : "No keepsakes."}
          </Text>
          <Text style={styles.note}>
            {profile.data?.profile.unlocks.species.length
              ? `Bloodlines held, not yet walked: ${profile.data.profile.unlocks.species.join(", ")}`
              : "No bloodline is held."}
          </Text>
          <View style={{ height: 18 }} />
          <GhostButton
            testID="abandon-life-button"
            label="Abandon this life"
            onPress={() => {
              lifeRef.current?.dismiss();
              abandonRef.current?.present();
            }}
          />
        </BottomSheetScrollView>
      </BottomSheetModal>
      <BottomSheetModal
        ref={abandonRef}
        snapPoints={["36%"]}
        backgroundStyle={{ backgroundColor: colors.surface }}
        handleIndicatorStyle={{ backgroundColor: colors.accent }}
      >
        <View style={styles.sheet} testID="abandon-sheet">
          <Text style={styles.sheetTitle}>Close the record?</Text>
          <Text style={styles.note}>Marks you already earned stay. This life will not.</Text>
          <View style={{ height: 16 }} />
          <PrimaryButton
            testID="confirm-abandon-button"
            label={abandon.isPending ? "Closing..." : "Abandon"}
            disabled={abandon.isPending}
            onPress={() => void closeRecord()}
          />
        </View>
      </BottomSheetModal>
    </Screen>
  );
}

function Header({ save }: { save: Save }) {
  const styles = useStyles();
  const stage = STAGE[save.character.stage] ?? save.character.stage;
  return (
    <>
      <View style={styles.topRow}>
        <Text style={styles.name}>{save.character.name}</Text>
        <Text style={styles.money}>{moneyLabel(save.character.stats.money)}</Text>
      </View>
      <Text style={styles.meta}>
        Age {save.character.age_years} · {stage} · Generation {save.generation}
      </Text>
    </>
  );
}
