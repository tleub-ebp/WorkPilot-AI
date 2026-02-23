import React, { createContext, useContext, useState, ReactNode, useEffect } from 'react';

interface ProviderContextType {
  selectedProvider: string;
  setSelectedProvider: (provider: string) => void;
}

const ProviderContext = createContext<ProviderContextType | undefined>(undefined);

export const ProviderContextProvider = ({ children }: { children: ReactNode }) => {
  const [selectedProvider, setSelectedProviderState] = useState<string>(() => {
    // Restaure depuis localStorage si disponible
    return localStorage.getItem('selectedProvider') || '';
  });

  const setSelectedProvider = (provider: string) => {
    setSelectedProviderState(provider);
    localStorage.setItem('selectedProvider', provider);
  };

  useEffect(() => {
    // Synchronise le provider au montage
    const stored = localStorage.getItem('selectedProvider');
    if (stored && stored !== selectedProvider) {
      setSelectedProviderState(stored);
    }
  }, []);

  useEffect(() => {
    // Au montage, communique le provider sélectionné au backend
    if (selectedProvider && window.electronAPI?.selectProvider) {
      window.electronAPI.selectProvider(selectedProvider).catch(error => {
        console.error('Failed to sync provider selection to backend on mount:', error);
      });
    }
  }, [selectedProvider]);

  return (
    <ProviderContext.Provider value={{ selectedProvider, setSelectedProvider }}>
      {children}
    </ProviderContext.Provider>
  );
};

export const useProviderContext = () => {
  const context = useContext(ProviderContext);
  if (!context) {
    throw new Error('useProviderContext must be used within a ProviderContextProvider');
  }
  return context;
};