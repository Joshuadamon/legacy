import { BottomSheetModal, BottomSheetView } from "@gorhom/bottom-sheet";
import { useRouter } from "expo-router";
import { useMemo, useRef, useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";

import { ApiError } from "../src/api";
import { GhostButton, PrimaryButton, Screen, Toast, hapticError, hapticSuccess } from "../src/components/game-ui";
import { colors, fonts, makeStyles } from "../src/theme";
import { useBuyPack, useStore, type StorePack } from "../src/use-game";

const CHIP_LABEL: Record<string, string> = {
  all: "All",
  career: "Career",
  skills: "Skills",
  cosmetic: "Cosmetic",
  lifestyle: "Lifestyle",
  supernatural: "Supernatural",
};

const useStyles = makeStyles((palette) => ({
  scroll: { paddingHorizontal: 24, paddingBottom: 28 },
  kicker: {
    color: palette.accent,
    fontFamily: fonts.uiMedium,
    letterSpacing: 1.4,
    fontSize: 12,
    marginTop: 18,
  },
  balance: { color: palette.text, fontFamily: fonts.display, fontSize: 40, marginTop: 6 },
  unit: { color: palette.textMuted, fontFamily: fonts.ui, fontSize: 15, marginBottom: 14 },
  chipRow: { flexDirection: "row", alignItems: "center", gap: 8, paddingVertical: 8, paddingHorizontal: 24 },
  chip: {
    borderColor: palette.line,
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 8,
    backgroundColor: palette.surface,
  },
  chipOn: { borderColor: palette.accent, backgroundColor: palette.surfaceRaised },
  chipText: { color: palette.text, fontFamily: fonts.uiMedium, fontSize: 14 },
  card: {
    borderColor: palette.line,
    borderWidth: 1,
    backgroundColor: palette.surface,
    borderRadius: 12,
    padding: 14,
    marginBottom: 12,
  },
  cardTitle: { color: palette.text, fontFamily: fonts.display, fontSize: 22 },
  cost: { color: palette.accent, fontFamily: fonts.uiMedium, fontSize: 14, marginTop: 4 },
  blurb: { color: palette.textMuted, fontFamily: fonts.body, fontSize: 15, lineHeight: 22, marginVertical: 8 },
  sheet: { paddingHorizontal: 22, paddingBottom: 28 },
  sheetTitle: { color: palette.text, fontFamily: fonts.display, fontSize: 28, marginBottom: 8 },
  note: { color: palette.textMuted, fontFamily: fonts.body, fontSize: 16, marginBottom: 16 },
}));

export default function StoreScreen() {
  const styles = useStyles();
  const router = useRouter();
  const store = useStore();
  const buy = useBuyPack();
  const [category, setCategory] = useState("all");
  const [toast, setToast] = useState<string | null>(null);
  const [pending, setPending] = useState<StorePack | null>(null);
  const sheet = useRef<BottomSheetModal>(null);
  const snaps = useMemo(() => ["46%"], []);
  const chips = ["all", ...(store.data?.categories ?? [])];
  const packs = (store.data?.packs ?? []).filter((pack) => category === "all" || pack.category === category);

  function ask(pack: StorePack) {
    if (pack.owned) return;
    if ((store.data?.marks ?? 0) < pack.cost) {
      void hapticError();
      setToast("Not enough Legacy Marks.");
      return;
    }
    setPending(pack);
    setToast(null);
    sheet.current?.present();
  }

  async function confirm() {
    if (!pending) return;
    try {
      await buy.mutateAsync(pending.id);
      void hapticSuccess();
      sheet.current?.dismiss();
      setToast(`${pending.name} is yours.`);
      setPending(null);
    } catch (error) {
      void hapticError();
      setToast(error instanceof ApiError ? error.message : "The purchase did not land.");
    }
  }

  return (
    <Screen testID="store-screen">
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={{ flexGrow: 0 }}
        contentContainerStyle={styles.chipRow}
      >
        {chips.map((chip) => {
          const on = chip === category;
          return (
            <GhostChip
              key={chip}
              testID={`store-chip-${chip}`}
              label={CHIP_LABEL[chip] ?? chip}
              selected={on}
              onPress={() => setCategory(chip)}
            />
          );
        })}
      </ScrollView>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.kicker}>STORE</Text>
        <Text testID="marks-balance" style={styles.balance}>
          {store.data?.marks ?? "—"}
        </Text>
        <Text style={styles.unit}>Legacy Marks · {store.data?.lives_lived ?? 0} lives lived</Text>
        <Toast message={toast} />
        {packs.map((pack) => (
          <View key={pack.id} testID={`pack-${pack.id}`} style={styles.card}>
            <Text style={styles.cardTitle}>{pack.name}</Text>
            <Text style={styles.cost}>{pack.cost} marks</Text>
            <Text style={styles.blurb}>{pack.blurb}</Text>
            <GhostButton
              testID={`buy-${pack.id}`}
              label={pack.owned ? "Kept" : "Buy"}
              disabled={pack.owned || buy.isPending}
              onPress={() => ask(pack)}
            />
          </View>
        ))}
        <GhostButton testID="store-back-button" label="Back to the year" onPress={() => router.back()} />
      </ScrollView>
      <BottomSheetModal
        ref={sheet}
        snapPoints={snaps}
        backgroundStyle={{ backgroundColor: colors.surface }}
        handleIndicatorStyle={{ backgroundColor: colors.accent }}
      >
        <BottomSheetView style={styles.sheet} testID="buy-sheet">
          <Text style={styles.sheetTitle}>{pending?.name}</Text>
          <Text style={styles.note}>Spend {pending?.cost} Legacy Marks. This stays with you across lives.</Text>
          <PrimaryButton
            testID="confirm-buy-button"
            label={buy.isPending ? "Spending..." : "Confirm"}
            disabled={buy.isPending}
            onPress={() => void confirm()}
          />
        </BottomSheetView>
      </BottomSheetModal>
    </Screen>
  );
}

function GhostChip({
  label,
  selected,
  onPress,
  testID,
}: {
  label: string;
  selected: boolean;
  onPress: () => void;
  testID: string;
}) {
  const styles = useStyles();
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityState={{ selected }}
      onPress={onPress}
      style={[styles.chip, selected ? styles.chipOn : null]}
    >
      <Text style={styles.chipText}>{label}</Text>
    </Pressable>
  );
}
