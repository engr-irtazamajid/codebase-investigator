import { create } from 'zustand';
import { Message, RepoInfo } from '@/types';

interface ConversationState {
  sessionId: string | null;
  repoInfo: RepoInfo | null;
  messages: Message[];
  isIngesting: boolean;
  isLoading: boolean;
  error: string | null;

  setSession: (sessionId: string, repoInfo: RepoInfo) => void;
  addMessage: (message: Message) => void;
  updateMessage: (id: string, patch: Partial<Message>) => void;
  setIngesting: (v: boolean) => void;
  setLoading: (v: boolean) => void;
  setError: (err: string | null) => void;
  reset: () => void;
}

const initialState = {
  sessionId: null,
  repoInfo: null,
  messages: [],
  isIngesting: false,
  isLoading: false,
  error: null,
};

export const useConversationStore = create<ConversationState>((set) => ({
  ...initialState,

  setSession: (sessionId, repoInfo) =>
    set({ sessionId, repoInfo, messages: [], error: null }),

  addMessage: (message) =>
    set((s) => ({ messages: [...s.messages, message] })),

  updateMessage: (id, patch) =>
    set((s) => ({
      messages: s.messages.map((m) => (m.id === id ? { ...m, ...patch } : m)),
    })),

  setIngesting: (v) => set({ isIngesting: v }),
  setLoading: (v) => set({ isLoading: v }),
  setError: (err) => set({ error: err }),
  reset: () => set(initialState),
}));
