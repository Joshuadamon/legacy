import { BottomSheetModal, BottomSheetView } from "@gorhom/bottom-sheet";
import * as Linking from "expo-linking";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { Platform, Pressable, ScrollView, Text, View } from "react-native";

import { ApiError } from "../src/api";
import { GhostButton, PrimaryButton, Screen, Toast, hapticError, hapticSuccess } from "../src/components/game-ui";
import { colors, fonts, makeStyles } from "../src/theme";
import { useBuyPack, useStore, useVerifyPurchase, useWebCheckout, type CoinPack, type StorePack } from "../src/use-game";

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
    color: palette.textMuted,
    fontFamily: fonts.uiMedium,
    letterSpacing: 1.4,
    fontSize: 12,
    marginTop: 18,
    borderTopWidth: 1,
    borderTopColor: palette.gold,
    paddingTop: 12,
  },
  balances: { flexDirection: "row", gap: 28, marginBottom: 8 },
  balanceMarks: { color: palette.bone, fontFamily: fonts.display, fontSize: 40, marginTop: 6 },
  balanceCoins: { color: palette.gold, fontFamily: fonts.display, fontSize: 40, marginTop: 6 },
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
  chipOn: { borderColor: palette.gold, backgroundColor: palette.surfaceRaised },
  chipText: { color: palette.text, fontFamily: fonts.uiMedium, fontSize: 14 },
  chipTextOn: { color: palette.gold },
  card: {
    borderColor: palette.line,
    borderWidth: 1,
    backgroundColor: palette.surface,
    borderRadius: 12,
    padding: 14,
    marginBottom: 12,
  },
  cardTitle: { color: palette.text, fontFamily: fonts.display, fontSize: 22 },
  coinTitle: { color: palette.gold },
  costMarks: { color: palette.bone, fontFamily: fonts.uiMedium, fontSize: 14, marginTop: 4 },
  costCoins: { color: palette.gold, fontFamily: fonts.uiMedium, fontSize: 14, marginTop: 4 },
  price: { color: palette.textMuted, fontFamily: fonts.uiMedium, fontSize: 14, marginTop: 4 },
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
  const verify = useVerifyPurchase();
  const checkout = useWebCheckout();
  const params = useLocalSearchParams<{ checkout?: string }>();
  const onWeb = Platform.OS === "web";
  const [category, setCategory] = useState("all");
  const [toast, setToast] = useState<string | null>(null);
  const [pending, setPending] = useState<StorePack | null>(null);
  const sheet = useRef<BottomSheetModal>(null);
  const snaps = useMemo(() => ["46%"], []);
  const chips = ["all", ...(store.data?.categories ?? [])];
  const packs = (store.data?.packs ?? []).filter((pack) => category === "all" || pack.category === category);

  useEffect(() => {
    if (!onWeb) return;
    if (params.checkout === "success") {
      setToast("Payment received. Coins land in this browser's wallet when Stripe confirms them.");
      void store.refetch();
    } else if (params.checkout === "cancel") {
      setToast("Checkout canceled.");
    }
  }, [onWeb, params.checkout, store]);

  function ask(pack: StorePack) {
    if (pack.owned) return;
    const currency = pack.currency === "coins" ? "coins" : "marks";
    const balance = currency === "coins" ? (store.data?.coins ?? 0) : (store.data?.marks ?? 0);
    if (balance < pack.cost) {
      void hapticError();
      setToast(currency === "coins" ? "Not enough Coins." : "Not enough Legacy Marks.");
      return;
    }
    setPending(pack);
    setToast(null);
    sheet.current?.present();
  }

  async function buyCoinsOnWeb(packId: string) {
    setToast(null);
    try {
      const result = await checkout.mutateAsync(packId);
      if (result.url) await Linking.openURL(result.url);
    } catch (error) {
      void hapticError();
      setToast(error instanceof ApiError ? error.message : "Checkout could not be opened.");
    }
  }

  async function buyCoins(productId: string, amount: number) {
    setToast(null);
    try {
      await verify.mutateAsync({ product_id: productId });
      void hapticSuccess();
      setToast(`TEST purchase added ${amount} Coins.`);
    } catch (error) {
      void hapticError();
      setToast(error instanceof ApiError ? error.message : "The purchase could not be verified.");
    }
  }

  async function toggleImmortal() {
    if (!store.data?.subscription) return;
    setToast(null);
    const next = !store.data.subscription.active;
    try {
      await verify.mutateAsync({ product_id: store.data.subscription.product_id, active: next });
      void hapticSuccess();
      setToast(next ? "TEST immortality is on." : "TEST immortality has lapsed.");
    } catch (error) {
      void hapticError();
      setToast(error instanceof ApiError ? error.message : "The subscription could not be verified.");
    }
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
        style={{ flexGrow: 0, flexShrink: 0 }}
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
        <View style={styles.balances}>
          <View>
            <Text testID="marks-balance" style={styles.balanceMarks}>
              {store.data?.marks ?? "—"}
            </Text>
            <Text style={styles.unit}>Legacy Marks</Text>
          </View>
          <View>
            <Text testID="coins-balance" style={styles.balanceCoins}>
              {store.data?.coins ?? "—"}
            </Text>
            <Text style={styles.unit}>Coins</Text>
          </View>
        </View>
        <Text style={styles.unit}>{store.data?.lives_lived ?? 0} lives lived</Text>
        <Toast message={toast} />
        {packs.map((pack) => (
          <View key={pack.id} testID={`pack-${pack.id}`} style={styles.card}>
            <Text style={styles.cardTitle}>{pack.name}</Text>
            <Text style={pack.currency === "coins" ? styles.costCoins : styles.costMarks}>
              {pack.cost} {pack.currency === "coins" ? "coins" : "marks"}
            </Text>
            <Text style={styles.blurb}>{pack.blurb}</Text>
            <GhostButton
              testID={`buy-${pack.id}`}
              label={pack.owned ? "Kept" : "Buy"}
              disabled={pack.owned || buy.isPending}
              onPress={() => ask(pack)}
            />
          </View>
        ))}
        <Text style={styles.kicker}>GET COINS</Text>
        {onWeb ? (
          <WebCoinShop packs={store.data?.coin_packs ?? []} pending={checkout.isPending} onBuy={(id) => void buyCoinsOnWeb(id)} />
        ) : (
          <>
            <Text style={styles.blurb}>Bought coins. Marks stay earned. These buttons are TEST until the store is live.</Text>
            <View testID="coin-packs">
              {(store.data?.coin_packs ?? []).map((pack) => (
                <View key={pack.id} testID={`coin-pack-${pack.id}`} style={styles.card}>
                  <Text style={[styles.cardTitle, styles.coinTitle]}>{pack.coins} Coins</Text>
                  <Text style={styles.price}>{pack.price_label}</Text>
                  <GhostButton
                    testID={`buy-${pack.id}`}
                    label={verify.isPending ? "Checking..." : `TEST · ${pack.price_label}`}
                    disabled={verify.isPending}
                    onPress={() => void buyCoins(pack.product_id, pack.coins)}
                  />
                </View>
              ))}
            </View>
          </>
        )}
        <Text style={styles.kicker}>IMMORTALITY</Text>
        <View testID="immortal-offer" style={styles.card}>
          <Text style={styles.cardTitle}>Ageless</Text>
          <Text testID="immortal-terms" style={styles.blurb}>
            {store.data?.subscription.terms ?? "$14.99/month, auto-renews until canceled."}
          </Text>
          <Text style={styles.note}>The body does not age. It can still be killed. Canceling lets the years resume.</Text>
          <GhostButton
            testID="test-immortal-toggle"
            label={
              verify.isPending
                ? "Checking..."
                : store.data?.subscription.active
                  ? "TEST · End immortality"
                  : "TEST · $14.99/month"
            }
            disabled={verify.isPending || !store.data?.subscription}
            onPress={() => void toggleImmortal()}
          />
        </View>
        <GhostButton testID="store-back-button" label="Back to the year" onPress={() => router.back()} />
      </ScrollView>
      <BottomSheetModal
        ref={sheet}
        snapPoints={snaps}
        backgroundStyle={{ backgroundColor: colors.surfaceRaised }}
        handleIndicatorStyle={{ backgroundColor: colors.gold }}
      >
        <BottomSheetView style={styles.sheet} testID="buy-sheet">
          <Text style={styles.sheetTitle}>{pending?.name}</Text>
          <Text style={styles.note}>
            Spend {pending?.cost} {pending?.currency === "coins" ? "Coins" : "Legacy Marks"}. This stays with you across
            lives.
          </Text>
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

function WebCoinShop({
  packs,
  pending,
  onBuy,
}: {
  packs: CoinPack[];
  pending: boolean;
  onBuy: (packId: string) => void;
}) {
  const styles = useStyles();
  return (
    <>
      <Text style={styles.blurb}>Bought coins stay in this browser's wallet. Marks stay earned.</Text>
      <View testID="coin-packs">
        {packs.map((pack) => (
          <View key={pack.id} testID={`coin-pack-${pack.id}`} style={styles.card}>
            <Text style={[styles.cardTitle, styles.coinTitle]}>{pack.coins} Coins</Text>
            <Text style={styles.price}>{pack.price_label}</Text>
            <GhostButton
              testID={`buy-${pack.id}`}
              label={pending ? "Opening checkout..." : `Get · ${pack.price_label}`}
              disabled={pending}
              onPress={() => onBuy(pack.id)}
            />
          </View>
        ))}
      </View>
    </>
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
      style={(state) => {
        const hovered = Boolean((state as { hovered?: boolean }).hovered);
        return [
          styles.chip,
          selected || hovered ? styles.chipOn : null,
          Platform.OS === "web" ? { cursor: "pointer" } : null,
        ];
      }}
    >
      <Text style={[styles.chipText, selected ? styles.chipTextOn : null]}>{label}</Text>
    </Pressable>
  );
}
