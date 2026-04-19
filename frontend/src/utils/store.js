import { create } from 'zustand';

const useStore = create((set, get) => ({
  // Auth
  user: null,
  token: null,
  setUser: (user, token) => set({ user, token }),
  logout: () => set({ user: null, token: null }),

  // Plants catalog
  plants: [],
  setPlants: (plants) => set({ plants }),

  // Garden image
  gardenImage: null,      // { id, url, width, height }
  setGardenImage: (img) => set({ gardenImage: img }),

  // Placed plants on canvas
  placedPlants: [],
  setPlacedPlants: (plants) => set({ placedPlants: plants }),
  addPlacedPlant: (item) => set((s) => ({ placedPlants: [...s.placedPlants, item] })),
  updatePlacedPlant: (id, updates) => set((s) => ({
    placedPlants: s.placedPlants.map((p) => p.id === id ? { ...p, ...updates } : p),
  })),
  removePlacedPlant: (id) => set((s) => ({
    placedPlants: s.placedPlants.filter((p) => p.id !== id),
    selectedId: s.selectedId === id ? null : s.selectedId,
  })),
  clearPlacedPlants: () => set({ placedPlants: [], selectedId: null }),

  // Selection
  selectedId: null,
  setSelectedId: (id) => set({ selectedId: id }),

  // UI state
  isGenerating: false,
  setIsGenerating: (v) => set({ isGenerating: v }),
  showStyleModal: false,
  setShowStyleModal: (v) => set({ showStyleModal: v }),
}));

export default useStore;
