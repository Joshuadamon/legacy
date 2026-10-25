import { createContext, createElement, useContext, useMemo, type ReactNode } from "react";
import { StyleSheet } from "react-native";

export const colors = {
  background: "#0E0E10",
  surface: "#17171B",
  surfaceRaised: "#1F1F24",
  text: "#F2EDE4",
  textMuted: "#8A8578",
  textFaint: "#8A8578",
  accent: "#C9A227",
  danger: "#C0392B",
  line: "#2A2A30",
  border: "#2A2A30",
  good: "#6B8E4E",
  ember: "#FF6B1A",
  emberDeep: "#B33C0A",
  gold: "#C9A227",
  blood: "#8E1B1B",
  success: "#6B8E4E",
  bone: "#8A8578",
  moon: "#B8BCC4",
} as const;

export type LifePalette = { [K in keyof typeof colors]: string };

/**
 * Life-path themes: the game's whole vibe shifts to fit the life being lived.
 * Species wins first (a vampire's night looks nothing like a priest's morning),
 * then career field, then moral signals, then the ember default.
 */
export const lifeThemes: Record<string, { label: string; palette: LifePalette }> = {
  default: {
    label: "Ember",
    palette: colors,
  },
  vampire: {
    label: "Blood Moon",
    palette: {
      ...colors,
      background: "#0A0508",
      surface: "#160A10",
      surfaceRaised: "#1E0E16",
      text: "#EDE3E6",
      textMuted: "#9A8490",
      accent: "#8E1B1B",
      ember: "#C0392B",
      emberDeep: "#7B1414",
      gold: "#B8BCC4",
      line: "#2A1620",
      border: "#2A1620",
    },
  },
  lycanthrope: {
    label: "Wild Moon",
    palette: {
      ...colors,
      background: "#070D07",
      surface: "#0E1A0E",
      surfaceRaised: "#142414",
      text: "#E6EDE0",
      textMuted: "#7E8F7A",
      accent: "#C9A227",
      ember: "#D4A017",
      emberDeep: "#8A6D00",
      gold: "#B8BCC4",
      moon: "#E8ECF0",
      line: "#1E2A1E",
      border: "#1E2A1E",
    },
  },
  witch: {
    label: "Hedge Craft",
    palette: {
      ...colors,
      background: "#0B0812",
      surface: "#150E22",
      surfaceRaised: "#1D1430",
      text: "#E9E4F0",
      textMuted: "#8F86A3",
      accent: "#7D5BA6",
      ember: "#9B7ED9",
      emberDeep: "#6A4FA3",
      gold: "#C9A227",
      line: "#241C38",
      border: "#241C38",
    },
  },
  crime: {
    label: "Street Noir",
    palette: {
      ...colors,
      background: "#0A0A0C",
      surface: "#141416",
      surfaceRaised: "#1C1C20",
      text: "#E8E8E8",
      textMuted: "#7A7A80",
      accent: "#E63946",
      ember: "#FF2D2D",
      emberDeep: "#A31621",
      gold: "#C9A227",
      line: "#26262A",
      border: "#26262A",
    },
  },
  priest: {
    label: "Sanctuary",
    palette: {
      ...colors,
      background: "#120D06",
      surface: "#1C150A",
      surfaceRaised: "#261D0E",
      text: "#F2E8D0",
      textMuted: "#9A8A68",
      accent: "#E8C874",
      ember: "#F5D47A",
      emberDeep: "#C9A227",
      gold: "#E8C874",
      line: "#2E2412",
      border: "#2E2412",
    },
  },
  doctor: {
    label: "Clinical",
    palette: {
      ...colors,
      background: "#0A0E12",
      surface: "#111820",
      surfaceRaised: "#182230",
      text: "#E4EDF2",
      textMuted: "#7E93A3",
      accent: "#5BA8C9",
      ember: "#7EC8E3",
      emberDeep: "#4A90B8",
      gold: "#C9A227",
      line: "#1E2A36",
      border: "#1E2A36",
    },
  },
  author: {
    label: "Ink & Paper",
    palette: {
      ...colors,
      background: "#14100A",
      surface: "#1E1810",
      surfaceRaised: "#282114",
      text: "#EDE0C8",
      textMuted: "#8A7A5E",
      accent: "#C9A227",
      ember: "#D4A017",
      emberDeep: "#8A6D00",
      gold: "#C9A227",
      line: "#2A2214",
      border: "#2A2214",
    },
  },
  scholar: {
    label: "Library",
    palette: {
      ...colors,
      background: "#081009",
      surface: "#0E1A10",
      surfaceRaised: "#142414",
      text: "#E2EDE2",
      textMuted: "#7E8F7E",
      accent: "#6B8E4E",
      ember: "#8FBC6A",
      emberDeep: "#5A7A3E",
      gold: "#C9A227",
      line: "#1C2A1C",
      border: "#1C2A1C",
    },
  },
  artist: {
    label: "Bohemian",
    palette: {
      ...colors,
      background: "#0E0812",
      surface: "#180E20",
      surfaceRaised: "#201430",
      text: "#EDE4F0",
      textMuted: "#9A86A3",
      accent: "#C86BD9",
      ember: "#D98FE8",
      emberDeep: "#A35AB8",
      gold: "#E8C874",
      line: "#281C38",
      border: "#281C38",
    },
  },
  soldier: {
    label: "Field",
    palette: {
      ...colors,
      background: "#0C0E08",
      surface: "#14180E",
      surfaceRaised: "#1C2214",
      text: "#E6EAD8",
      textMuted: "#8A9078",
      accent: "#8A9A5B",
      ember: "#A8B87A",
      emberDeep: "#6A7A45",
      gold: "#C9A227",
      line: "#22281A",
      border: "#22281A",
    },
  },
  law: {
    label: "Authority",
    palette: {
      ...colors,
      background: "#080C12",
      surface: "#0E1620",
      surfaceRaised: "#141E2C",
      text: "#E0E8F0",
      textMuted: "#7E8FA3",
      accent: "#5B7EA6",
      ember: "#7EA6C9",
      emberDeep: "#4A6A8A",
      gold: "#C9A227",
      line: "#1C2634",
      border: "#1C2634",
    },
  },
  merchant: {
    label: "Gilded",
    palette: {
      ...colors,
      background: "#100E06",
      surface: "#1A160A",
      surfaceRaised: "#241E0E",
      text: "#F0E8D0",
      textMuted: "#9A8F6E",
      accent: "#E8C874",
      ember: "#F5D47A",
      emberDeep: "#C9A227",
      gold: "#F5D47A",
      line: "#2C2412",
      border: "#2C2412",
    },
  },
  outlaw: {
    label: "Outlaw",
    palette: {
      ...colors,
      background: "#0D0605",
      surface: "#180C0A",
      surfaceRaised: "#201210",
      text: "#EDE0DC",
      textMuted: "#8F7A74",
      accent: "#C0392B",
      ember: "#E63946",
      emberDeep: "#8E1B1B",
      gold: "#C9A227",
      line: "#2A1A16",
      border: "#2A1A16",
    },
  },
  faithful: {
    label: "Devout",
    palette: {
      ...colors,
      background: "#0E0C10",
      surface: "#161220",
      surfaceRaised: "#1E1A2E",
      text: "#E8E4F0",
      textMuted: "#8A86A3",
      accent: "#E8C874",
      ember: "#F5D47A",
      emberDeep: "#C9A227",
      gold: "#E8C874",
      line: "#221E32",
      border: "#221E32",
    },
  },
};

export type LifeThemeKey = keyof typeof lifeThemes;

export type LifeCharacter = {
  species?: string | null;
  career?: { field?: string | null } | null;
  flags?: { morality?: number; faith?: number } | null;
} | null | undefined;

/** Career field (lowercased) -> life theme. Add fields as new careers ship. */
const careerThemeMap: Record<string, LifeThemeKey> = {
  crime: "crime",
  criminal: "crime",
  underworld: "crime",
  theft: "crime",
  priest: "priest",
  clergy: "priest",
  ministry: "priest",
  pastor: "priest",
  doctor: "doctor",
  medicine: "doctor",
  medical: "doctor",
  surgeon: "doctor",
  nurse: "doctor",
  author: "author",
  writer: "author",
  writing: "author",
  scholar: "scholar",
  teacher: "scholar",
  education: "scholar",
  professor: "scholar",
  scientist: "scholar",
  artist: "artist",
  art: "artist",
  musician: "artist",
  music: "artist",
  soldier: "soldier",
  military: "soldier",
  law: "law",
  police: "law",
  legal: "law",
  judge: "law",
  merchant: "merchant",
  business: "merchant",
  trade: "merchant",
  entrepreneur: "merchant",
};

export function resolveLifeTheme(character: LifeCharacter): LifeThemeKey {
  if (!character) return "default";
  const species = (character.species ?? "").toLowerCase();
  if (species.includes("vampire")) return "vampire";
  if (species.includes("lycan") || species.includes("werewolf")) return "lycanthrope";
  if (species.includes("witch") || species.includes("warlock")) return "witch";
  const field = (character.career?.field ?? "").toLowerCase();
  if (field && careerThemeMap[field]) return careerThemeMap[field];
  const morality = character.flags?.morality ?? 50;
  const faith = character.flags?.faith ?? 50;
  if (morality < 25) return "outlaw";
  if (faith > 75) return "faithful";
  return "default";
}

const LifeThemeContext = createContext<LifePalette>(colors);

export function LifeThemeProvider({
  character,
  children,
}: {
  character: LifeCharacter;
  children: ReactNode;
}) {
  const palette = useMemo(() => {
    const key = resolveLifeTheme(character);
    return lifeThemes[key].palette;
  }, [character?.species, character?.career?.field, character?.flags?.morality, character?.flags?.faith]);
  return createElement(LifeThemeContext.Provider, { value: palette }, children);
}

export function useLifeThemeKey(character: LifeCharacter): LifeThemeKey {
  return useMemo(() => resolveLifeTheme(character), [character]);
}

export const fonts = {
  display: "Literata_600SemiBold",
  body: "SourceSans3_400Regular",
  ui: "SourceSans3_400Regular",
  uiMedium: "SourceSans3_600SemiBold",
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
} as const;

export const radius = {
  sm: 6,
  md: 12,
  lg: 20,
} as const;

export function useTheme() {
  const palette = useContext(LifeThemeContext);
  return { colors: palette, fonts, spacing, radius };
}

export function makeStyles<T extends StyleSheet.NamedStyles<T>>(
  factory: (palette: LifePalette) => T,
) {
  return function useStyles() {
    const { colors: palette } = useTheme();
    return useMemo(() => StyleSheet.create(factory(palette)), [palette]);
  };
}
