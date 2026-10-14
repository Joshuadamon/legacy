import { useRouter } from "expo-router";
import { useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";

import { ApiError, api } from "../src/api";
import { GhostButton, Screen, Toast, hapticError, moneyLabel } from "../src/components/game-ui";
import { colors, fonts, makeStyles } from "../src/theme";
import {
  type ActivityResult,
  type ChoiceDeltas,
  type GameActivity,
  type Stats,
  useActivities,
  usePerformActivity,
} from "../src/use-game";

const useStyles = makeStyles((palette) => ({
  scroll: { paddingHorizontal: 22, paddingBottom: 24 },
  kicker: {
    color: palette.textMuted,
    fontFamily: fonts.uiMedium,
    letterSpacing: 1.4,
    fontSize: 12,
    marginTop: 18,
    marginBottom: 4,
  },
  title: { color: palette.text, fontFamily: fonts.display, fontSize: 34, marginBottom: 6 },
  note: { color: palette.textMuted, fontFamily: fonts.body, fontSize: 15, lineHeight: 22, marginBottom: 16 },
  categoryHeader: {
    color: palette.gold,
    fontFamily: fonts.uiMedium,
    fontSize: 13,
    letterSpacing: 1.2,
    marginTop: 18,
    marginBottom: 8,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 14,
    paddingHorizontal: 16,
    borderColor: palette.line,
    borderWidth: 1,
    borderRadius: 12,
    marginBottom: 8,
    backgroundColor: palette.surface,
  },
  rowLocked: { opacity: 0.45 },
  icon: { fontSize: 28, marginRight: 14, width: 36, textAlign: "center" },
  rowBody: { flex: 1 },
  rowName: { color: palette.text, fontFamily: fonts.uiMedium, fontSize: 17 },
  rowDesc: { color: palette.textMuted, fontFamily: fonts.body, fontSize: 14, marginTop: 2 },
  rowLock: { color: palette.textMuted, fontFamily: fonts.ui, fontSize: 12, marginTop: 4, fontStyle: "italic" },
  chevron: { color: palette.gold, fontSize: 20, marginLeft: 8 },
  resultCard: {
    backgroundColor: palette.surfaceRaised,
    borderColor: palette.gold,
    borderWidth: 1,
    borderRadius: 12,
    padding: 18,
    marginBottom: 18,
  },
  resultTitle: { color: palette.text, fontFamily: fonts.display, fontSize: 24, marginBottom: 8 },
  resultNarrative: { color: palette.text, fontFamily: fonts.body, fontSize: 16, lineHeight: 25, marginBottom: 12 },
  resultOutcome: { color: palette.textMuted, fontFamily: fonts.body, fontSize: 15, lineHeight: 23, marginBottom: 10 },
  deltaRow: { flexDirection: "row", flexWrap: "wrap", gap: 10, marginTop: 6 },
  deltaUp: { color: "#7dcea0", fontFamily: fonts.uiMedium, fontSize: 14 },
  deltaDown: { color: "#e5989b", fontFamily: fonts.uiMedium, fontSize: 14 },
  backRow: { marginTop: 8 },
}));

const CATEGORY_LABEL: Record<string, string> = {
  risk: "Risk",
  social: "Social",
  health: "Health",
  lifestyle: "Lifestyle",
};

const CATEGORY_ORDER = ["risk", "social", "health", "lifestyle"];

function signedChange(key: string, value: number): string {
  if (key === "money") return value > 0 ? `+${moneyLabel(value)}` : moneyLabel(value);
  return value > 0 ? `+${value}` : String(value);
}

const STAT_LABELS: Record<string, string> = {
  health: "Health",
  happiness: "Happiness",
  smarts: "Smarts",
  looks: "Looks",
  money: "Money",
  reputation: "Reputation",
  family: "Family",
};

export default function ActivitiesScreen() {
  const styles = useStyles();
  const router = useRouter();
  const activities = useActivities();
  const perform = usePerformActivity();
  const [toast, setToast] = useState<string | null>(null);
  const [result, setResult] = useState<ActivityResult | null>(null);

  async function doActivity(id: string) {
    setToast(null);
    setResult(null);
    try {
      const data = await perform.mutateAsync(id);
      setResult(data);
    } catch (error) {
      void hapticError();
      setToast(error instanceof ApiError ? error.message : "The activity did not happen.");
    }
  }

  function closeResult() {
    setResult(null);
  }

  const list = activities.data?.activities ?? [];
  const grouped: Record<string, GameActivity[]> = {};
  for (const a of list) {
    const cat = a.category || "lifestyle";
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(a);
  }

  return (
    <Screen testID="activities-screen">
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.kicker}>ACTIVITIES</Text>
        <Text style={styles.title}>What will you do?</Text>
        <Text style={styles.note}>
          Actions don't cost you time — the seasons turn on their own. Do as much as you dare.
        </Text>
        <Toast message={toast} />

        {result ? (
          <View style={styles.resultCard} testID="activity-result">
            <Text style={styles.resultTitle}>{result.activity.title}</Text>
            <Text style={styles.resultNarrative}>{result.activity.narrative}</Text>
            <Text style={styles.resultOutcome}>{result.activity.outcome}</Text>
            <View style={styles.deltaRow}>
              {Object.entries(result.deltas.stats ?? {}).map(([key, value]) => (
                <Text key={key} style={value > 0 ? styles.deltaUp : styles.deltaDown}>
                  {STAT_LABELS[key] ?? key} {signedChange(key, value)}
                </Text>
              ))}
              {result.deltas.money !== 0 ? (
                <Text style={result.deltas.money > 0 ? styles.deltaUp : styles.deltaDown}>
                  {signedChange("money", result.deltas.money)}
                </Text>
              ) : null}
            </View>
            <View style={styles.backRow}>
              <GhostButton testID="activity-back-button" label="Back to activities" onPress={closeResult} />
            </View>
          </View>
        ) : null}

        {activities.isPending ? <Text style={styles.note}>Loading activities...</Text> : null}

        {CATEGORY_ORDER.map((cat) => {
          const items = grouped[cat] ?? [];
          if (items.length === 0) return null;
          return (
            <View key={cat}>
              <Text style={styles.categoryHeader}>{CATEGORY_LABEL[cat] ?? cat}</Text>
              {items.map((a) => (
                <Pressable
                  key={a.id}
                  testID={`activity-${a.id}`}
                  accessibilityRole="button"
                  disabled={!a.available || perform.isPending}
                  onPress={() => void doActivity(a.id)}
                  style={[styles.row, !a.available ? styles.rowLocked : null]}
                >
                  <Text style={styles.icon}>{a.icon}</Text>
                  <View style={styles.rowBody}>
                    <Text style={styles.rowName}>{a.name}</Text>
                    <Text style={styles.rowDesc}>{a.description}</Text>
                    {!a.available && a.locked_reason ? (
                      <Text style={styles.rowLock}>{a.locked_reason}</Text>
                    ) : null}
                    {a.cost_money > 0 && a.available ? (
                      <Text style={styles.rowLock}>{moneyLabel(a.cost_money)}</Text>
                    ) : null}
                  </View>
                  {a.available ? <Text style={styles.chevron}>›</Text> : null}
                </Pressable>
              ))}
            </View>
          );
        })}

        <View style={styles.backRow}>
          <GhostButton testID="activities-back-button" label="Back to the life" onPress={() => router.back()} />
        </View>
      </ScrollView>
    </Screen>
  );
}
