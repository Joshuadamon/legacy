import "react-native-gesture-handler";

import { BottomSheetModalProvider } from "@gorhom/bottom-sheet";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useFonts } from "expo-font";
import { Stack, useRouter, useSegments } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { Literata_400Regular, Literata_600SemiBold } from "@expo-google-fonts/literata";
import { SourceSans3_400Regular, SourceSans3_600SemiBold } from "@expo-google-fonts/source-sans-3";
import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, StyleSheet, View } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { KeyboardProvider } from "react-native-keyboard-controller";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { AuthProvider, useAuth } from "../src/auth-context";
import { ErrorBoundary } from "../src/components/error-boundary";
import { colors } from "../src/theme";
import { WebStage } from "../src/web-stage";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1 } },
});

function Gate() {
  const { status, user } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (status === "loading") return;
    const onLogin = segments[0] === "login";
    const onAge = segments[0] === "age";
    if (status === "null" && !onLogin && !onAge) router.replace("/age");
    if (status === "user" && onLogin) router.replace(user?.age_confirmed ? "/" : "/age");
    if (status === "user" && onAge && user?.age_confirmed) router.replace("/");
  }, [status, segments, router, user?.age_confirmed]);

  if (status === "loading") {
    return (
      <View style={styles.boot}>
        <ActivityIndicator color={colors.ember} />
      </View>
    );
  }

  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.background },
        animation: "fade",
      }}
    />
  );
}

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({
    Literata_400Regular,
    Literata_600SemiBold,
    SourceSans3_400Regular,
    SourceSans3_600SemiBold,
  });
  // Boot must never hang on fonts. expo-font verifies web fonts with a
  // ~12s FontObserver timeout and swallows the failure; without a backstop
  // the boot spinner below renders forever with no error surfaced.
  const [fontTimedOut, setFontTimedOut] = useState(false);
  const loggedFontError = useRef(false);

  useEffect(() => {
    if (fontsLoaded || fontError) return;
    const id = setTimeout(() => setFontTimedOut(true), 15000);
    return () => clearTimeout(id);
  }, [fontsLoaded, fontError]);

  useEffect(() => {
    if (fontError && !loggedFontError.current) {
      loggedFontError.current = true;
      console.error("[LEGACY] web fonts failed to load, continuing with system fonts:", fontError);
    }
  }, [fontError]);

  const fontsReady = fontsLoaded || fontError != null || fontTimedOut;

  if (!fontsReady) {
    return (
      <WebStage>
        <View style={styles.boot}>
          <ActivityIndicator color={colors.ember} />
        </View>
      </WebStage>
    );
  }

  return (
    <GestureHandlerRootView style={styles.root}>
      <KeyboardProvider>
        <SafeAreaProvider>
          <ErrorBoundary>
            <QueryClientProvider client={queryClient}>
              <AuthProvider>
                <BottomSheetModalProvider>
                  <StatusBar style="light" />
                  <WebStage>
                    <Gate />
                  </WebStage>
                </BottomSheetModalProvider>
              </AuthProvider>
            </QueryClientProvider>
          </ErrorBoundary>
        </SafeAreaProvider>
      </KeyboardProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.background },
  boot: {
    flex: 1,
    backgroundColor: colors.background,
    alignItems: "center",
    justifyContent: "center",
  },
});
