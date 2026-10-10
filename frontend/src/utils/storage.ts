import AsyncStorage from "@react-native-async-storage/async-storage";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

export async function getItem(key: string): Promise<string | null> {
  if (Platform.OS === "web") {
    return window.localStorage.getItem(key);
  }
  return AsyncStorage.getItem(key);
}

export async function setItem(key: string, value: string): Promise<void> {
  if (Platform.OS === "web") {
    window.localStorage.setItem(key, value);
    return;
  }
  await AsyncStorage.setItem(key, value);
}

export async function secureGet(key: string): Promise<string | null> {
  if (Platform.OS === "web") {
    return window.localStorage.getItem(`secure:${key}`) || null;
  }
  try {
    return (await SecureStore.getItemAsync(key)) || null;
  } catch {
    return AsyncStorage.getItem(`secure:${key}`);
  }
}

export async function secureSet(key: string, value: string): Promise<void> {
  if (Platform.OS === "web") {
    if (!value) window.localStorage.removeItem(`secure:${key}`);
    else window.localStorage.setItem(`secure:${key}`, value);
    return;
  }
  if (!value) {
    try {
      await SecureStore.deleteItemAsync(key);
    } catch {
      await AsyncStorage.removeItem(`secure:${key}`);
    }
    return;
  }
  try {
    await SecureStore.setItemAsync(key, value);
  } catch {
    await AsyncStorage.setItem(`secure:${key}`, value);
  }
}
