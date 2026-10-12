import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api";
import { useAuth } from "./auth-context";

export type Stats = {
  health: number;
  happiness: number;
  smarts: number;
  looks: number;
  money: number;
  reputation: number;
  family: number;
};

export type Flags = {
  morality: number;
  honesty: number;
  discipline: number;
  aggression: number;
  addiction: number;
  faith: number;
  nature: number;
  ambition: number;
  charisma: number;
  resilience: number;
};

export type Child = { id: string; name: string; born_parent_age: number; other_parent?: string };

export type Partner = { name: string; status: "dating" | "married"; bond: number } | null;
export type Career = { title: string; field: string; level: number; income: number } | null;
export type Business = { name: string; type: string; value: number } | null;

export type Choice = {
  label: string;
  outcome: string;
  effects: Partial<Stats>;
  flags: Partial<Flags>;
  milestone?: string;
  fatal?: boolean;
  child_born?: boolean;
  child_name?: string;
  partner_set?: { name: string; status: "dating" | "married" };
  partner_end?: boolean;
  career_start?: { title: string; field: string };
  career_level?: "up" | "down";
  career_leave?: boolean;
  business_start?: { name: string; type: string };
  business_event?: number;
  species_effects?: {
    bloodlust?: number;
    masquerade?: number;
    hunter_heat?: number;
    moon?: number;
    control?: number;
    mana?: number;
    notoriety?: number;
  };
};

export type Circle = { name: string; members: string[] };

export type VampireData = {
  clan: string;
  bloodlust: number;
  masquerade: number;
  last_power_age: number | null;
};

export type LycanData = {
  subtype: string;
  moon: number;
  control: number;
  pack: Circle | null;
  last_power_age: number | null;
};

export type WitchData = {
  mana: number;
  notoriety: number;
  coven: Circle | null;
  last_power_age: number | null;
};

export type SpeciesData = VampireData | LycanData | WitchData;

export type GameEvent = { title: string; narrative: string; choices: Choice[] };

export type Character = {
  name: string;
  background: string;
  background_key: string;
  age_years: number;
  stage: string;
  stats: Stats;
  flags: Flags;
  life_log: string[];
  unlocked_paths: string[];
  children: Child[];
  partner: Partner;
  career: Career;
  business: Business;
  species: string;
  species_data: SpeciesData | null;
  hunter_heat: number;
  applied_grants: string[];
};

export type HistoryYear = { age: number; title: string; choice: string; outcome: string };

export type LineageEntry = {
  generation: number;
  name: string;
  years: string;
  cause_of_death: string | null;
  partner: { name: string; status: "dating" | "married" } | string | null;
  heir_id: string;
  heir_name: string;
  epitaph: string;
};

export type Save = {
  user_id: string;
  generation: number;
  alive: boolean;
  cause_of_death: string | null;
  character: Character;
  current_event: GameEvent | null;
  last_outcome: string | null;
  history: HistoryYear[];
  lineage: LineageEntry[];
  marks_earned: number;
  true_death: boolean;
};

export type Profile = {
  user_id: string;
  marks: number;
  owned_packs: string[];
  lives_lived: number;
  unlocks: { careers: string[]; cosmetics: string[]; species: string[] };
};

export type StorePack = {
  id: string;
  category: string;
  name: string;
  blurb: string;
  cost: number;
  owned: boolean;
};

export type HeirOption = { id: string; name: string; age_now: number; kind: "child" | "new" };

export function useGameState() {
  const { status } = useAuth();
  return useQuery({
    queryKey: ["game", "state"],
    queryFn: () => api<{ save: Save | null }>("/api/game/state"),
    enabled: status === "user",
  });
}

export function useBackgrounds() {
  const { status } = useAuth();
  return useQuery({
    queryKey: ["game", "backgrounds"],
    queryFn: () =>
      api<{
        backgrounds: { key: string; label: string; blurb: string }[];
        vampire_clans: string[];
        lycan_subtypes: string[];
      }>("/api/game/backgrounds"),
    enabled: status === "user",
  });
}

export function useProfile() {
  const { status } = useAuth();
  return useQuery({
    queryKey: ["profile"],
    queryFn: () => api<{ profile: Profile }>("/api/profile"),
    enabled: status === "user",
  });
}

export function useStore() {
  const { status } = useAuth();
  return useQuery({
    queryKey: ["store"],
    queryFn: () =>
      api<{ marks: number; lives_lived: number; categories: string[]; packs: StorePack[] }>("/api/store"),
    enabled: status === "user",
  });
}

export function useHeirs(enabled: boolean) {
  return useQuery({
    queryKey: ["game", "heirs"],
    queryFn: () =>
      api<{ obituary: string; marks_earned: number; marks_balance: number; heirs: HeirOption[] }>("/api/game/heirs"),
    enabled,
  });
}

function useInvalidateLife() {
  const client = useQueryClient();
  return async () => {
    await client.invalidateQueries({ queryKey: ["game"] });
    await client.invalidateQueries({ queryKey: ["profile"] });
    await client.invalidateQueries({ queryKey: ["store"] });
  };
}

function useGameClient() {
  return useQueryClient();
}

export function useNewGame() {
  const refresh = useInvalidateLife();
  const client = useGameClient();
  return useMutation({
    mutationFn: (body: { name: string; background_key: string; species?: string; clan?: string; subtype?: string }) =>
      api<{ save: Save }>("/api/game/new", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: async (data) => {
      client.setQueryData(["game", "state"], data);
      await refresh();
    },
  });
}

export function useChoice() {
  const refresh = useInvalidateLife();
  return useMutation({
    mutationFn: (choice_index: number) =>
      api<{ save: Save; profile: Profile; marks_earned: number }>("/api/game/choice", {
        method: "POST",
        body: JSON.stringify({ choice_index }),
      }),
    onSuccess: refresh,
  });
}

export function useContinueHeir() {
  const refresh = useInvalidateLife();
  return useMutation({
    mutationFn: (body: { heir_id: string; name?: string }) =>
      api<{ save: Save }>("/api/game/heir", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: refresh,
  });
}

export function useAbandon() {
  const refresh = useInvalidateLife();
  return useMutation({
    mutationFn: () => api<{ ok: boolean }>("/api/game/abandon", { method: "POST" }),
    onSuccess: refresh,
  });
}

export function useTransform() {
  const refresh = useInvalidateLife();
  return useMutation({
    mutationFn: (body: { species: string; clan?: string; subtype?: string }) =>
      api<{ save: Save }>("/api/game/transform", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: refresh,
  });
}

export function useSupernatural() {
  const refresh = useInvalidateLife();
  return useMutation({
    mutationFn: (action: string) =>
      api<{ save: Save; outcome: string }>("/api/game/supernatural", {
        method: "POST",
        body: JSON.stringify({ action }),
      }),
    onSuccess: refresh,
  });
}

export function useBuyPack() {
  const refresh = useInvalidateLife();
  return useMutation({
    mutationFn: (pack_id: string) =>
      api<{ profile: Profile; pack_id: string }>("/api/store/buy", {
        method: "POST",
        body: JSON.stringify({ pack_id }),
      }),
    onSuccess: refresh,
  });
}
