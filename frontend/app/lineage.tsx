import { useRouter } from "expo-router";
import { ScrollView, Text, View } from "react-native";

import { GhostButton, Screen, StatLine } from "../src/components/game-ui";
import { fonts, makeStyles } from "../src/theme";
import { useGameState } from "../src/use-game";

const useStyles = makeStyles((palette) => ({
  scroll: { paddingHorizontal: 24, paddingBottom: 32 },
  kicker: {
    color: palette.accent,
    fontFamily: fonts.uiMedium,
    letterSpacing: 1.4,
    fontSize: 12,
    marginTop: 18,
  },
  title: { color: palette.text, fontFamily: fonts.display, fontSize: 34, marginVertical: 8 },
  card: {
    borderColor: palette.line,
    borderWidth: 1,
    backgroundColor: palette.surface,
    borderRadius: 12,
    padding: 14,
    marginBottom: 12,
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
  const line = save?.lineage ?? [];

  return (
    <Screen testID="lineage-screen">
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.kicker}>FAMILY</Text>
        <Text style={styles.title}>The line</Text>
        {line.length === 0 ? <Text style={styles.body}>You are the first of the line.</Text> : null}
        {line.map((entry) => (
          <View key={`${entry.generation}-${entry.name}`} style={styles.card} testID={`ancestor-${entry.generation}`}>
            <Text style={styles.name}>
              Gen {entry.generation} · {entry.name}
            </Text>
            <Text style={styles.body}>{entry.epitaph}</Text>
            <StatLine label="Years" value={entry.years} />
            <StatLine label="Continued as" value={entry.heir_name} />
            {entry.partner ? <StatLine label="Partner" value={entry.partner} /> : null}
          </View>
        ))}
        {save ? (
          <View style={styles.card} testID="living-card">
            <Text style={styles.living}>LIVING</Text>
            <Text style={styles.name}>{save.character.name}</Text>
            <Text style={styles.body}>
              Age {save.character.age_years}. {save.character.background}
            </Text>
            <StatLine label="Children" value={save.character.children.length} />
          </View>
        ) : null}
        <GhostButton testID="lineage-back-button" label="Back to the year" onPress={() => router.back()} />
      </ScrollView>
    </Screen>
  );
}
