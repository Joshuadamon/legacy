import "react-native-gesture-handler";

import { BottomSheetModalProvider } from "@gorhom/bottom-sheet";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useFonts } from "expo-font";
import { Stack, useRouter, useSegments } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { Literata_400Regular, Literata_600SemiBold } from "@expo-google-fonts/literata";
import { SourceSans3_400Regular, SourceSans3_600SemiBold } from "@expo-google-fonts/source-sans-3";
import { useEffect } from "react";
import { ActivityIndicator, StyleSheet, View } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { KeyboardProvider } from "react-native-keyboard-controller";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { AuthProvider, useAuth } from "../src/auth-context";
import { ErrorBoundary } from "../src/components/error-boundary";
import { colors } from "../src/theme";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1 } },
});

function Gate() {
  const { status } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (status === "loading") return;
    const onLogin = segments[0] === "login";
    if (status === "null" && !onLogin) router.replace("/login");
    if (status === "user" && onLogin) router.replace("/");
  }, [status, segments, router]);

  if (status === "loading") {
    return (
      <View style={styles.boot}>
        <ActivityIndicator color={colors.accent} />
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
  const [fontsLoaded] = useFonts({
    Literata_400Regular,
    Literata_600SemiBold,
    SourceSans3_400Regular,
    SourceSans3_600SemiBold,
  });

  if (!fontsLoaded) {
    return (
      <View style={styles.boot}>
        <ActivityIndicator color={colors.accent} />
      </View>
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
                  <Gate />
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
