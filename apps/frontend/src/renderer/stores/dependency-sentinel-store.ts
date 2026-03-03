import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

interface DependencySentinelState {
  isOpen: boolean;
  setIsDialogOpen: (open: boolean) => void;
  openDialog: () => void;
  closeDialog: () => void;
}

export const useDependencySentinelStore = create<DependencySentinelState>()(
  subscribeWithSelector((set) => ({
    isOpen: false,
    setIsDialogOpen: (open) => set({ isOpen: open }),
    openDialog: () => set({ isOpen: true }),
    closeDialog: () => set({ isOpen: false }),
  }))
);

export const openDependencySentinelDialog = () => {
  useDependencySentinelStore.getState().openDialog();
};
