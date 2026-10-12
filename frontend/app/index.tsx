import { Redirect } from "expo-router";
import { ActivityIndicator, Text, View } from "react-native";

import { PrimaryButton, Screen } from "../src/components/game-ui";
import { colors, fonts, makeStyles } from "../src/theme";
import { useAuth } from "../src/auth-context";
import { useGameState } from "../src/use-game";

const useStyles = makeStyles((palette) => ({
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  error: { flex: 1, justifyContent: "center", padding: 24 },
  errorTitle: {
    color: palette.text,
    fontFamily: fonts.display,
    fontSize: 28,
    marginBottom: 12,
  },
}));

export default function Index() {
  const styles = useStyles();
  const state = useGameState();
  const { user } = useAuth();

  if (state.isLoading) {
    return (
      <Screen testID="index-loading">
        <View style={styles.center}>
          <ActivityIndicator color={colors.ember} />
        </View>
      </Screen>
    );
  }

  if (state.isError) {
    return (
      <Screen testID="index-error">
        <View style={styles.error}>
          <Text style={styles.errorTitle}>The record could not be opened.</Text>
          <PrimaryButton testID="state-retry-button" label="Try again" onPress={() => state.refetch()} />
        </View>
      </Screen>
    );
  }

  if (!state.data?.save && !user?.age_confirmed) return <Redirect href="/age" />;
  if (!state.data?.save) return <Redirect href="/create" />;
  if (!state.data.save.alive) return <Redirect href="/heir" />;
  return <Redirect href="/game" />;
}
