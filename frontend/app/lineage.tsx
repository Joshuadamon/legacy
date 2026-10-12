import { useRouter } from "expo-router";
import { ScrollView, Text, View } from "react-native";

import { GhostButton, Screen } from "../src/components/game-ui";
import { fonts, makeStyles } from "../src/theme";
import { formatAge, useGameState, type Character, type LineageEntry } from "../src/use-game";

const SPECIES_LABELS: Record<string, string> = {
  vampire: "Vampire",
  lycanthrope: "Lycanthrope",
  witch: "Witch",
};

function speciesLabel(species: string | undefined): string {
  if (!species || species === "human") return "Human";
  return SPECIES_LABELS[species] ?? species;
}

function partnerText(partner: NonNullable<LineageEntry["partner"]> | NonNullable<Character["partner"]>): string {
  if (typeof partner === "string") return partner;
  const status = partner.status === "married" ? "Married" : "Dating";
  return `${partner.name} · ${status}`;
}

function lifespanText(entry: LineageEntry): string {
  const years = entry.years?.trim();
  if (years) return years;
  return `0–${entry.age_at_death}`;
}

const useStyles = makeStyles((palette) => ({
  scroll: { flexGrow: 1 },
  content: { paddingHorizontal: 20, paddingBottom: 32 },
  kicker: {
    color: palette.textMuted,
    fontFamily: fonts.uiMedium,
    letterSpacing: 1.4,
    fontSize: 13,
    marginTop: 18,
    borderTopWidth: 1,
    borderTopColor: palette.gold,
    paddingTop: 12,
  },
  title: { color: palette.text, fontFamily: fonts.display, fontSize: 34, marginTop: 6, marginBottom: 8 },
  order: { color: palette.textMuted, fontFamily: fonts.body, fontSize: 15, lineHeight: 22, marginBottom: 16 },
  empty: { color: palette.textMuted, fontFamily: fonts.body, fontSize: 16, lineHeight: 22, marginBottom: 12 },
  node: {
    borderColor: palette.line,
    borderWidth: 1,
    backgroundColor: palette.surface,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  livingNode: { borderColor: palette.gold },
  gen: {
    color: palette.gold,
    fontFamily: fonts.uiMedium,
    fontSize: 13,
    letterSpacing: 1,
    marginBottom: 2,
  },
  name: { color: palette.text, fontFamily: fonts.display, fontSize: 22, lineHeight: 28 },
  line: { color: palette.text, fontFamily: fonts.body, fontSize: 16, lineHeight: 22, marginTop: 4 },
  muted: { color: palette.textMuted, fontFamily: fonts.body, fontSize: 16, lineHeight: 22, marginTop: 4 },
  spine: { alignItems: "center", paddingVertical: 2 },
  spineLine: { width: 1, height: 16, backgroundColor: palette.gold },
  spineLabel: {
    color: palette.textMuted,
    fontFamily: fonts.uiMedium,
    fontSize: 15,
    lineHeight: 20,
    textAlign: "center",
    paddingVertical: 2,
  },
  back: { marginTop: 16 },
}));

function AncestorNode({ entry }: { entry: LineageEntry }) {
  const styles = useStyles();
  const cause = entry.cause_of_death?.trim() || "The record does not say.";
  return (
    <View style={styles.node} testID={`ancestor-${entry.generation}`}>
      <Text style={styles.gen}>GENERATION {entry.generation}</Text>
      <Text style={styles.name}>{entry.name}</Text>
      <Text style={styles.line} testID={`ancestor-species-${entry.generation}`}>
        {speciesLabel(entry.species)}
      </Text>
      <Text style={styles.line} testID={`ancestor-lifespan-${entry.generation}`}>
        {lifespanText(entry)}
      </Text>
      <Text style={styles.muted} testID={`ancestor-cause-${entry.generation}`}>
        Died: {cause}
      </Text>
      <Text style={styles.line} testID={`ancestor-partner-${entry.generation}`}>
        Partner: {entry.partner ? partnerText(entry.partner) : "No partner"}
      </Text>
      <Text style={styles.line} testID={`ancestor-heir-${entry.generation}`}>
        Continued as {entry.heir_name}
      </Text>
    </View>
  );
}

function Connector({ generation, heir }: { generation: number; heir: string }) {
  const styles = useStyles();
  return (
    <View style={styles.spine} testID={`lineage-connector-${generation}`}>
      <View style={styles.spineLine} />
      <Text style={styles.spineLabel}>The line passed to {heir}</Text>
      <View style={styles.spineLine} />
    </View>
  );
}

function LivingNode({ character }: { character: Character }) {
  const styles = useStyles();
  const children = character.children.map((child) => child.name).filter(Boolean);
  return (
    <View style={[styles.node, styles.livingNode]} testID="living-card">
      <Text style={styles.gen}>LIVING</Text>
      <Text style={styles.name}>{character.name}</Text>
      <Text style={styles.line} testID="living-species">
        {speciesLabel(character.species)}
      </Text>
      <Text style={styles.line} testID="living-age">
        Age {formatAge(character.age_years, character.age_months)}
      </Text>
      <Text style={styles.line} testID="living-partner">
        Partner: {character.partner ? partnerText(character.partner) : "No partner"}
      </Text>
      <Text style={styles.muted} testID="living-children">
        Children: {children.length ? children.join(", ") : "None yet"}
      </Text>
    </View>
  );
}

export default function LineageScreen() {
  const styles = useStyles();
  const router = useRouter();
  const state = useGameState();
  const save = state.data?.save;
  const line = [...(save?.lineage ?? [])].sort((a, b) => a.generation - b.generation);

  return (
    <Screen testID="lineage-screen">
      <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
        <Text style={styles.kicker}>FAMILY</Text>
        <Text style={styles.title}>The line</Text>
        <Text style={styles.order}>Oldest at the top. The living life at the bottom.</Text>
        {line.length === 0 ? <Text style={styles.empty}>You are the first of the line.</Text> : null}
        {line.map((entry) => (
          <View key={`${entry.generation}-${entry.name}`}>
            <AncestorNode entry={entry} />
            <Connector generation={entry.generation} heir={entry.heir_name} />
          </View>
        ))}
        {save ? <LivingNode character={save.character} /> : null}
        <View style={styles.back}>
          <GhostButton testID="lineage-back-button" label="Back to the year" onPress={() => router.back()} />
        </View>
      </ScrollView>
    </Screen>
  );
}
