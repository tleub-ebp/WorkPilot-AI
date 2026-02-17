import React, { useState } from 'react';
import type { LLMProvider } from './types';

// TODO: Remplacer par l'ordre réel issu du store
const initialOrder: LLMProvider[] = [
  'claude', 'openai', 'mistral', 'gemini', 'grok', 'cohere', 'openrouter', 'groq', 'zai-global', 'zai-cn'
];

const PriorityOrder: React.FC = () => {
  const [order, setOrder] = useState(initialOrder);

  const move = (from: number, to: number) => {
    if (to < 0 || to >= order.length) return;
    const newOrder = [...order];
    const [item] = newOrder.splice(from, 1);
    newOrder.splice(to, 0, item);
    setOrder(newOrder);
  };

  return (
    <div>
      <h2 style={{ fontSize: 18, marginBottom: 8 }}>Ordre de priorité des connecteurs</h2>
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {order.map((provider, idx) => (
          <li key={provider} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{ flex: 1 }}>{provider}</span>
            <button onClick={() => move(idx, idx - 1)} disabled={idx === 0}>↑</button>
            <button onClick={() => move(idx, idx + 1)} disabled={idx === order.length - 1}>↓</button>
          </li>
        ))}
      </ul>
    </div>
  );
};
export default PriorityOrder;