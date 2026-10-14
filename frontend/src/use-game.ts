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
  age_quarters: number;
  age_years: number;
  age_months: number;
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
  species?: string;
  age_at_death?: number;
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
  coins: number;
  owned_packs: string[];
  lives_lived: number;
  immortal: boolean;
  unlocks: { careers: string[]; cosmetics: string[]; species: string[] };
};

export type StorePack = {
  id: string;
  category: string;
  name: string;
  blurb: string;
  cost: number;
  currency: "marks" | "coins";
  owned: boolean;
};

export type CoinPack = {
  id: string;
  product_id: string;
  coins: number;
  price_label: string;
};

export type ImmortalOffer = {
  product_id: string;
  entitlement: string;
  price_label: string;
  terms: string;
  active: boolean;
};

export type StoreCatalog = {
  marks: number;
  coins: number;
  lives_lived: number;
  categories: string[];
  packs: StorePack[];
  coin_packs: CoinPack[];
  subscription: ImmortalOffer;
};

export type Descendant = {
  id: string;
  name: string;
  age_years: number;
  age_months: number;
  age_quarters: number;
  generation_depth: number;
  relation: string;
};

export type HeirOption = {
  id: string;
  name: string;
  age_now: number;
  age_months?: number;
  age_quarters?: number;
  kind: "child" | "new";
};

export function formatAge(years: number, months = 0): string {
  if (!months) return `${years}y`;
  return `${years}y ${months}m`;
}

export function formatQuarters(quarters: number): string {
  const years = Math.floor(quarters / 4);
  const months = (quarters % 4) * 3;
  return formatAge(years, months);
}

export function powerSpentThisYear(lastPowerAge: number | null | undefined, ageQuarters: number): boolean {
  if (lastPowerAge == null) return false;
  return Math.floor(lastPowerAge / 4) === Math.floor(ageQuarters / 4);
}

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
    queryFn: () => api<StoreCatalog>("/api/store"),
    enabled: status === "user",
  });
}

export function useDescendants(enabled: boolean) {
  return useQuery({
    queryKey: ["game", "descendants"],
    queryFn: () => api<{ descendants: Descendant[] }>("/api/game/descendants"),
    enabled,
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

export type YearMontage = {
  text: string;
  lines: string[];
};

export type SkipResult = {
  years_skipped: number;
  montage: YearMontage;
  new_age: number;
  stat_changes: Partial<Stats>;
  save: Save;
};

export type ChoiceDeltas = {
  stats: Record<string, number>;
  flags: Record<string, number>;
  money: number;
  notes: string[];
};

export type ChoiceResult = {
  save: Save;
  profile: Profile;
  marks_earned: number;
  deltas: ChoiceDeltas;
};

export function useChoice() {
  const refresh = useInvalidateLife();
  return useMutation({
    mutationFn: (choice_index: number) =>
      api<ChoiceResult>("/api/game/choice", {
        method: "POST",
        body: JSON.stringify({ choice_index }),
      }),
    onSuccess: refresh,
  });
}

export function useSkip() {
  const refresh = useInvalidateLife();
  return useMutation({
    mutationFn: () => api<SkipResult>("/api/game/skip", { method: "POST" }),
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

export function useWebCheckout() {
  const refresh = useInvalidateLife();
  return useMutation({
    mutationFn: (pack_id: string) =>
      api<{ url: string }>("/api/store/web-checkout", {
        method: "POST",
        body: JSON.stringify({ pack_id }),
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

export const TEST_PURCHASE_RECEIPT = "legacy-test-receipt";

export function useVerifyPurchase() {
  const refresh = useInvalidateLife();
  return useMutation({
    mutationFn: (body: { product_id: string; active?: boolean }) =>
      api<{ profile: Profile; coins_granted: number; immortal: boolean; product_id: string }>(
        "/api/store/purchase/verify",
        {
          method: "POST",
          body: JSON.stringify({ ...body, receipt: TEST_PURCHASE_RECEIPT }),
        },
      ),
    onSuccess: refresh,
  });
}

export function usePassTorch() {
  const refresh = useInvalidateLife();
  return useMutation({
    mutationFn: (descendant_id: string) =>
      api<{ save: Save }>("/api/game/pass-torch", {
        method: "POST",
        body: JSON.stringify({ descendant_id }),
      }),
    onSuccess: refresh,
  });
}

export type GameActivity = {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  available: boolean;
  locked_reason: string | null;
  cost_money: number;
};

export type ActivityResult = {
  save: Save;
  profile: Profile;
  activity: {
    id: string;
    name: string;
    title: string;
    narrative: string;
    outcome: string;
  };
  deltas: ChoiceDeltas;
};

export function useActivities() {
  return useQuery({
    queryKey: ["activities"],
    queryFn: () => api<{ activities: GameActivity[] }>("/api/activities"),
  });
}

export function usePerformActivity() {
  const refresh = useInvalidateLife();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (activity_id: string) =>
      api<ActivityResult>("/api/activities/perform", {
        method: "POST",
        body: JSON.stringify({ activity_id }),
      }),
    onSuccess: (data) => {
      refresh();
      queryClient.invalidateQueries({ queryKey: ["activities"] });
    },
  });
}
