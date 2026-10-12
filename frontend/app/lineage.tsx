import { useRouter } from "expo-router";
import { ScrollView, Text, View } from "react-native";

import { GhostButton, Screen, StatLine } from "../src/components/game-ui";
import { fonts, makeStyles } from "../src/theme";
import { useGameState, type LineageEntry } from "../src/use-game";

const SPECIES_LABEL: Record<string, string> = {
  human: "Human",
  vampire: "Vampire",
  lycanthrope: "Lycanthrope",
  witch: "Witch",
};

function speciesLabel(species: string | undefined): string {
  if (!species) return "Human";
  return SPECIES_LABEL[species] ?? species;
}

function partnerText(partner: NonNullable<LineageEntry["partner"]>): string {
  if (typeof partner === "string") return partner;
  if (partner.status === "married") return `${partner.name} · Married`;
  if (partner.status === "dating") return `${partner.name} · Dating`;
  return partner.name;
}

const useStyles = makeStyles((palette) => ({
  scroll: { paddingHorizontal: 24, paddingBottom: 32 },
  kicker: {
    color: palette.accent,
    fontFamily: fonts.uiMedium,
    letterSpacing: 1.4,
    fontSize: 12,
    marginTop: 18,
  },
  title: { color: palette.text, fontFamily: fonts.display, fontSize: 34, marginTop: 8, marginBottom: 6 },
  order: { color: palette.textMuted, fontFamily: fonts.body, fontSize: 15, lineHeight: 22, marginBottom: 16 },
  tree: { marginTop: 4 },
  card: {
    borderColor: palette.line,
    borderWidth: 1,
    backgroundColor: palette.surface,
    borderRadius: 12,
    padding: 14,
  },
  livingCard: { borderColor: palette.accent },
  stem: { alignItems: "center", paddingVertical: 2 },
  stemLine: { width: 2, height: 14, backgroundColor: palette.accent },
  stemLabel: {
    color: palette.textMuted,
    fontFamily: fonts.ui,
    fontSize: 14,
    lineHeight: 20,
    marginVertical: 4,
    textAlign: "center",
  },
  name: { color: palette.text, fontFamily: fonts.display, fontSize: 22 },
  body: { color: palette.textMuted, fontFamily: fonts.body, fontSize: 15, lineHeight: 22, marginTop: 6 },
  living: { color: palette.accent, fontFamily: fonts.uiMedium, fontSize: 12, letterSpacing: 1, marginBottom: 4 },
}));

export default function LineageScreen() {
  const styles = useStyles();
  const router = useRouter();
  const state = useGameState();
  const save = state.data?.save;
  const line = [...(save?.lineage ?? [])].sort((a, b) => a.generation - b.generation);

  return (
    <Screen testID="lineage-screen">
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.kicker}>FAMILY</Text>
        <Text style={styles.title}>The line</Text>
        <Text style={styles.order}>Oldest at the top. The living life at the bottom.</Text>
        {line.length === 0 ? <Text style={styles.body}>You are the first of the line.</Text> : null}
        <View style={styles.tree} testID="lineage-tree">
          {line.map((entry) => (
            <View key={`${entry.generation}-${entry.name}`}>
              <View style={styles.card} testID={`ancestor-${entry.generation}`}>
                <Text style={styles.name}>
                  Gen {entry.generation} · {entry.name}
                </Text>
                <StatLine label="Species" value={speciesLabel(entry.species)} />
                <StatLine label="Died at" value={entry.age_at_death} />
                <StatLine label="Cause" value={entry.cause_of_death || "The record does not say."} />
                <StatLine label="Partner" value={entry.partner ? partnerText(entry.partner) : "None"} />
                <StatLine label="Continued as" value={entry.heir_name} />
              </View>
              <View style={styles.stem} testID={`lineage-stem-${entry.generation}`}>
                <View style={styles.stemLine} />
                <Text style={styles.stemLabel}>The line passed to {entry.heir_name}</Text>
                <View style={styles.stemLine} />
              </View>
            </View>
          ))}
          {save ? (
            <View style={[styles.card, styles.livingCard]} testID="living-card">
              <Text style={styles.living}>LIVING</Text>
              <Text style={styles.name}>
                Gen {save.generation} · {save.character.name}
              </Text>
              <StatLine label="Species" value={speciesLabel(save.character.species)} />
              <StatLine label="Age" value={save.character.age_years} />
              <StatLine
                label="Partner"
                value={save.character.partner ? partnerText(save.character.partner) : "None"}
              />
            </View>
          ) : null}
        </View>
        <View style={{ height: 16 }} />
        <GhostButton testID="lineage-back-button" label="Back to the year" onPress={() => router.back()} />
      </ScrollView>
    </Screen>
  );
}
