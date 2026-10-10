import { Component, type ReactNode } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { colors, fonts, spacing } from "../theme";

type Props = { children: ReactNode };
type State = { error: Error | null };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <View style={styles.wrap}>
        <Text style={styles.title}>The line snagged.</Text>
        <Text style={styles.body}>{this.state.error.message}</Text>
        <Pressable
          testID="error-boundary-retry"
          accessibilityRole="button"
          onPress={() => this.setState({ error: null })}
          style={styles.button}
        >
          <Text style={styles.buttonText}>Try again</Text>
        </Pressable>
      </View>
    );
  }
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    backgroundColor: colors.background,
    padding: spacing.lg,
    justifyContent: "center",
  },
  title: {
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 28,
    marginBottom: spacing.sm,
  },
  body: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 16,
    marginBottom: spacing.lg,
  },
  button: {
    alignSelf: "flex-start",
    borderColor: colors.accent,
    borderWidth: 1,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  buttonText: {
    color: colors.accent,
    fontFamily: fonts.uiMedium,
    fontSize: 16,
  },
});
