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
  hapticTap,
  moneyLabel,
} from "../src/components/game-ui";
import { colors, fonts, makeStyles } from "../src/theme";
import {
  useAbandon,
  useBackgrounds,
  useChoice,
  useGameState,
  useProfile,
  useSupernatural,
  useTransform,
  type Circle,
  type Flags,
  type LycanData,
  type Save,
  type VampireData,
  type WitchData,
} from "../src/use-game";

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

  chips: { flexDirection: "row", gap: 8, paddingVertical: 8 },
  chip: {
    borderColor: palette.line,
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 8,
    backgroundColor: palette.surface,
  },
  chipOn: { borderColor: palette.accent },
  chipText: { color: palette.text, fontFamily: fonts.ui, fontSize: 15 },
  powers: { gap: 10, marginTop: 12 },
}));

const StyleSheetAbsolute = { position: "absolute" as const, left: 0, right: 0, top: 0, bottom: 0 };

const PLAYABLE = new Set(["vampire", "lycanthrope", "witch"]);

const YEARLY: Record<string, { id: string; label: string }[]> = {
  vampire: [
    { id: "feed", label: "Feed" },
    { id: "lay_low", label: "Lay low" },
    { id: "seek_clan", label: "Seek the clan" },
  ],
  lycanthrope: [
    { id: "run_pack", label: "Run with the pack" },
    { id: "isolate", label: "Isolate" },
    { id: "hunt", label: "Hunt" },
  ],
  witch: [
    { id: "ritual", label: "Perform a ritual" },
    { id: "lay_low", label: "Lay low" },
    { id: "hex_rival", label: "Hex a rival" },
  ],
};

const TURN_COPY: Record<string, { title: string; ask: string; button: string; testID: string }> = {
  vampire: { title: "The Thirst", ask: "The blood will take, if you ask it.", button: "Take the blood", testID: "transform-vampire-button" },
  lycanthrope: { title: "The Moon", ask: "The bite will take, if you ask it.", button: "Take the bite", testID: "transform-lycanthrope-button" },
  witch: { title: "The Craft", ask: "The working will wake, if you ask it.", button: "Awaken", testID: "transform-witch-button" },
};

function bloodlineNotes(held: string[], walking: string): string[] {
  const notes: string[] = [];
  if (walking === "vampire" || held.includes("vampire")) {
    notes.push(walking === "vampire" ? "You walk the Thirst." : "The Thirst is open.");
  }
  if (walking === "lycanthrope" || held.includes("lycanthrope")) {
    notes.push(walking === "lycanthrope" ? "You answer the Moon." : "The Moon is open.");
  }
  if (walking === "witch" || held.includes("witch")) {
    notes.push(walking === "witch" ? "You keep a working." : "The Craft is open.");
  }
  const waiting = held.filter((item) => !PLAYABLE.has(item));
  if (waiting.length) notes.push(`Bloodlines held, not yet walked: ${waiting.join(", ")}`);
  if (!notes.length) notes.push("No bloodline is held.");
  return notes;
}

function circleLine(circle: Circle | null): string {
  if (!circle) return "No circle is kept.";
  return circle.members.length ? `${circle.name} · ${circle.members.join(", ")}` : circle.name;
}

function asVampire(save: Save): VampireData | null {
  const data = save.character.species_data;
  if (save.character.species !== "vampire" || !data || !("bloodlust" in data)) return null;
  return data;
}

function asLycan(save: Save): LycanData | null {
  const data = save.character.species_data;
  if (save.character.species !== "lycanthrope" || !data || !("control" in data)) return null;
  return data;
}

function asWitch(save: Save): WitchData | null {
  const data = save.character.species_data;
  if (save.character.species !== "witch" || !data || !("mana" in data)) return null;
  return data;
}

function howTheyMet(log: string[], name: string): string {
  const line = log.find((entry) => entry.includes(name));
  return line ?? "The record does not say how you met.";
}

function clanSlug(clan: string): string {
  return clan.toLowerCase().replace(/\s+/g, "-");
}

export default function GameScreen() {
  const styles = useStyles();
  const router = useRouter();
  const state = useGameState();
  const profile = useProfile();
  const choice = useChoice();
  const abandon = useAbandon();
  const turn = useTransform();
  const power = useSupernatural();
  const backgrounds = useBackgrounds();
  const lifeRef = useRef<BottomSheetModal>(null);
  const abandonRef = useRef<BottomSheetModal>(null);
  const powersRef = useRef<BottomSheetModal>(null);
  const snaps = useMemo(() => ["78%"], []);
  const [toast, setToast] = useState<string | null>(null);
  const [partnerOpen, setPartnerOpen] = useState(false);
  const [clan, setClan] = useState("");
  const [subtype, setSubtype] = useState("");
  const [turnSpecies, setTurnSpecies] = useState<"vampire" | "lycanthrope" | "witch">("vampire");
  const save = state.data?.save;
  const clans = backgrounds.data?.vampire_clans ?? [];
  const subtypes = backgrounds.data?.lycan_subtypes ?? [];
  const chosenClan = clan || clans[0] || "";
  const chosenSubtype = subtype || subtypes[0] || "";
  const held = profile.data?.profile.unlocks.species ?? [];
  const holdsThirst = held.includes("vampire");
  const holdsMoon = held.includes("lycanthrope");
  const holdsCraft = held.includes("witch");
  const turnOptions = [
    ...(holdsThirst ? [{ id: "vampire" as const, label: "Vampire" }] : []),
    ...(holdsMoon ? [{ id: "lycanthrope" as const, label: "Lycanthrope" }] : []),
    ...(holdsCraft ? [{ id: "witch" as const, label: "Witch" }] : []),
  ];
  const chosenTurn = turnOptions.some((item) => item.id === turnSpecies) ? turnSpecies : turnOptions[0]?.id;

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

  async function takeChange() {
    if (!chosenTurn) return;
    setToast(null);
    try {
      await turn.mutateAsync({
        species: chosenTurn,
        clan: chosenTurn === "vampire" ? chosenClan : undefined,
        subtype: chosenTurn === "lycanthrope" ? chosenSubtype : undefined,
      });
      powersRef.current?.dismiss();
    } catch (error) {
      void hapticError();
      setToast(error instanceof ApiError ? error.message : "The change did not take.");
    }
  }

  async function spendPower(action: string) {
    setToast(null);
    try {
      const result = await power.mutateAsync(action);
      setToast(result.outcome);
      if (!result.save.alive) router.replace("/heir");
    } catch (error) {
      void hapticError();
      setToast(error instanceof ApiError ? error.message : "The night did not answer.");
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

  const vampire = asVampire(save);
  const lycan = asLycan(save);
  const witch = asWitch(save);
  const walking = vampire ?? lycan ?? witch;
  const powerSpent = walking?.last_power_age === save.character.age_years;
  const yearly = YEARLY[save.character.species] ?? [];
  const showPowers = Boolean(walking) || holdsThirst || holdsMoon || holdsCraft;
  const turnCopy = chosenTurn ? TURN_COPY[chosenTurn] : null;

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
        {showPowers ? (
          <GhostButton fill testID="open-powers-sheet" label="Powers" onPress={() => powersRef.current?.present()} />
        ) : null}
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
          <Text style={styles.section}>PARTNER</Text>
          {save.character.partner ? (
            <>
              <Pressable
                testID="partner-row"
                accessibilityRole="button"
                onPress={() => {
                  void hapticTap();
                  setPartnerOpen((open) => !open);
                }}
              >
                <StatLine
                  label={save.character.partner.name}
                  value={save.character.partner.status === "married" ? "Married" : "Dating"}
                />
              </Pressable>
              <View style={styles.meters}>
                <Meter label="Bond" value={save.character.partner.bond} />
              </View>
              {partnerOpen ? (
                <Text testID="partner-detail" style={styles.note}>
                  {howTheyMet(save.character.life_log, save.character.partner.name)}
                </Text>
              ) : null}
            </>
          ) : (
            <Text style={styles.note}>No one is written beside you.</Text>
          )}
          <Text style={styles.section}>FLAGS</Text>
          {FLAG_LABELS.map((flag) => (
            <StatLine key={flag.key} label={flag.label} value={save.character.flags[flag.key]} />
          ))}
          <Text style={styles.section}>CHILDREN</Text>
          {save.character.children.length === 0 ? <Text style={styles.note}>None yet.</Text> : null}
          {save.character.children.map((child) => (
            <StatLine
              key={child.id}
              label={child.name}
              value={
                child.other_parent
                  ? `born at ${child.born_parent_age}, with ${child.other_parent}`
                  : `born at ${child.born_parent_age}`
              }
            />
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
          {bloodlineNotes(held, save.character.species).map((line) => (
            <Text key={line} style={styles.note}>
              {line}
            </Text>
          ))}
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
      <BottomSheetModal
        ref={powersRef}
        snapPoints={snaps}
        backgroundStyle={{ backgroundColor: colors.surface }}
        handleIndicatorStyle={{ backgroundColor: colors.accent }}
      >
        <BottomSheetScrollView contentContainerStyle={styles.sheet} testID="powers-sheet">
          <Text style={styles.sheetTitle}>
            {vampire ? "The Thirst" : lycan ? "The Moon" : witch ? "The Craft" : "Powers"}
          </Text>
          {vampire ? (
            <>
              <Text style={styles.note}>{vampire.clan}</Text>
              <View style={styles.meters}>
                <Meter label="Bloodlust" value={vampire.bloodlust} />
                <Meter label="Masquerade" value={vampire.masquerade} />
                <Meter label="Hunter heat" value={save.character.hunter_heat} />
              </View>
            </>
          ) : null}
          {lycan ? (
            <>
              <Text style={styles.note}>{lycan.subtype}</Text>
              <Text style={styles.note}>{circleLine(lycan.pack)}</Text>
              <View style={styles.meters}>
                <Meter label="Moon" value={lycan.moon} />
                <Meter label="Control" value={lycan.control} />
                <Meter label="Hunter heat" value={save.character.hunter_heat} />
              </View>
            </>
          ) : null}
          {witch ? (
            <>
              <Text style={styles.note}>{circleLine(witch.coven)}</Text>
              <View style={styles.meters}>
                <Meter label="Mana" value={witch.mana} />
                <Meter label="Notoriety" value={witch.notoriety} />
                <Meter label="Hunter heat" value={save.character.hunter_heat} />
              </View>
            </>
          ) : null}
          {walking ? (
            <>
              <Text style={styles.section}>THIS YEAR</Text>
              {powerSpent ? <Text style={styles.note}>This year's power is spent.</Text> : null}
              <View style={styles.powers}>
                {yearly.map((item) => (
                  <GhostButton
                    key={item.id}
                    testID={`power-${item.id.replace(/_/g, "-")}`}
                    label={power.isPending ? "..." : item.label}
                    disabled={power.isPending || powerSpent}
                    onPress={() => void spendPower(item.id)}
                  />
                ))}
              </View>
            </>
          ) : (
            <>
              <Text style={styles.note}>
                {save.character.age_years >= 13 && turnCopy ? turnCopy.ask : "The change waits until thirteen."}
              </Text>
              {save.character.age_years >= 13 && turnCopy ? (
                <>
                  {turnOptions.length > 1 ? (
                    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
                      {turnOptions.map((item) => {
                        const selected = item.id === chosenTurn;
                        return (
                          <Pressable
                            key={item.id}
                            testID={`transform-species-${item.id}`}
                            accessibilityRole="button"
                            accessibilityState={{ selected }}
                            onPress={() => setTurnSpecies(item.id)}
                            style={[styles.chip, selected ? styles.chipOn : null]}
                          >
                            <Text style={styles.chipText}>{item.label}</Text>
                          </Pressable>
                        );
                      })}
                    </ScrollView>
                  ) : null}
                  {chosenTurn === "vampire" ? (
                    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
                      {clans.map((item) => {
                        const selected = item === chosenClan;
                        return (
                          <Pressable
                            key={item}
                            testID={`power-clan-${clanSlug(item)}`}
                            accessibilityRole="button"
                            accessibilityState={{ selected }}
                            onPress={() => setClan(item)}
                            style={[styles.chip, selected ? styles.chipOn : null]}
                          >
                            <Text style={styles.chipText}>{item}</Text>
                          </Pressable>
                        );
                      })}
                    </ScrollView>
                  ) : null}
                  {chosenTurn === "lycanthrope" ? (
                    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
                      {subtypes.map((item) => {
                        const selected = item === chosenSubtype;
                        return (
                          <Pressable
                            key={item}
                            testID={`power-subtype-${item}`}
                            accessibilityRole="button"
                            accessibilityState={{ selected }}
                            onPress={() => setSubtype(item)}
                            style={[styles.chip, selected ? styles.chipOn : null]}
                          >
                            <Text style={styles.chipText}>{item}</Text>
                          </Pressable>
                        );
                      })}
                    </ScrollView>
                  ) : null}
                  <PrimaryButton
                    testID={turnCopy.testID}
                    label={turn.isPending ? "Turning..." : turnCopy.button}
                    disabled={turn.isPending}
                    onPress={() => void takeChange()}
                  />
                </>
              ) : null}
            </>
          )}
        </BottomSheetScrollView>
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
        {asVampire(save) ? ` · ${asVampire(save)?.clan}` : ""}
        {asLycan(save) ? ` · ${asLycan(save)?.subtype}` : ""}
        {asWitch(save) ? " · the Craft" : ""}
      </Text>
    </>
  );
}
