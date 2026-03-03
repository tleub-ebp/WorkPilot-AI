import React, { createContext, useContext, useState, useMemo, ReactNode } from 'react';

interface ProviderContextType {
  selectedProvider: string;
  setSelectedProvider: (provider: string) => void;
}

const ProviderContext = createContext<ProviderContextType | undefined>(undefined);

interface ProviderContextProviderProps {
  children: ReactNode;
}

export const ProviderContextProvider: React.FC<ProviderContextProviderProps> = ({ children }) => {
  const [selectedProvider, setSelectedProvider] = useState<string>('');

  const contextValue = useMemo(() => ({
    selectedProvider,
    setSelectedProvider,
  }), [selectedProvider]);

  return (
    <ProviderContext.Provider value={contextValue}>
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
