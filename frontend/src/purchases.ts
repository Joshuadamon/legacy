import { Platform } from "react-native";

/**
 * Placeholder store keys. react-native-purchases is installed for the live
 * catalog. This TEST slice never calls Purchases.configure and never starts
 * a real purchase. Buttons go through the server test verifier instead.
 */
export const revenueCatAppleKey = process.env.EXPO_PUBLIC_REVENUECAT_APPLE_KEY ?? "";
export const revenueCatGoogleKey = process.env.EXPO_PUBLIC_REVENUECAT_GOOGLE_KEY ?? "";

export function purchasesReady(): boolean {
  return false;
}

export async function configurePurchasesIfLive(): Promise<void> {
  if (Platform.OS === "web") return;
  if (!revenueCatAppleKey && !revenueCatGoogleKey) return;
}
