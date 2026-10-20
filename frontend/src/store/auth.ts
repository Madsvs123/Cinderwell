import { create } from "zustand";

type AuthState = {
  access: string | null;
  name: string;
  organization: string;
  setSession: (access: string, name: string, organization: string) => void;
  clear: () => void;
};

export const useAuth = create<AuthState>((set) => ({
  access: null,
  name: "",
  organization: "",
  setSession: (access, name, organization) => set({ access, name, organization }),
  clear: () => set({ access: null, name: "", organization: "" }),
}));
