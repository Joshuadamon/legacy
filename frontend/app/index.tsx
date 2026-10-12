import { Redirect } from "expo-router";
import { ActivityIndicator, Text, View } from "react-native";

import { GhostButton, Screen } from "../src/components/game-ui";
import { colors, fonts } from "../src/theme";
import { useAuth } from "../src/auth-context";
import { useGameState } from "../src/use-game";

export default function Index() {
  const state = useGameState();
  const { user } = useAuth();

  if (state.isLoading) {
    return (
      <Screen testID="index-loading">
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center" }}>
          <ActivityIndicator color={colors.accent} />
        </View>
      </Screen>
    );
  }

  if (state.isError) {
    return (
      <Screen testID="index-error">
        <View style={{ flex: 1, justifyContent: "center", padding: 24 }}>
          <Text style={{ color: colors.text, fontFamily: fonts.display, fontSize: 28, marginBottom: 12 }}>
            The record could not be opened.
          </Text>
          <GhostButton testID="state-retry-button" label="Try again" onPress={() => state.refetch()} />
        </View>
      </Screen>
    );
  }

  if (!state.data?.save && !user?.age_confirmed) return <Redirect href="/age" />;
  if (!state.data?.save) return <Redirect href="/create" />;
  if (!state.data.save.alive) return <Redirect href="/heir" />;
  return <Redirect href="/game" />;
}
