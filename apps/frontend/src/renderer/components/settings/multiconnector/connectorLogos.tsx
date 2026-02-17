import AnthropicLogo from '../../../assets/logos/anthropic.svg';
import OpenAILogo from '../../../assets/logos/openai.svg';
import MistralLogo from '../../../assets/logos/mistral.svg';
import GeminiLogo from '../../../assets/logos/gemini.svg';
import GrokLogo from '../../../assets/logos/grok.svg';
import CohereLogo from '../../../assets/logos/cohere.svg';
import OpenRouterLogo from '../../../assets/logos/openrouter.svg';
import GroqLogo from '../../../assets/logos/groq.svg';
import ZaiGlobalLogo from '../../../assets/logos/zai-global.svg';
import ZaiChinaLogo from '../../../assets/logos/zai-china.svg';
import React from 'react';

export const connectorLogos: Record<string, React.ReactNode> = {
  'claude': <img src={AnthropicLogo} alt="Anthropic" className="h-8 w-8" />,
  'openai': <img src={OpenAILogo} alt="OpenAI" className="h-8 w-8" />,
  'mistral': <img src={MistralLogo} alt="Mistral" className="h-8 w-8" />,
  'gemini': <img src={GeminiLogo} alt="Gemini" className="h-8 w-8" />,
  'grok': <img src={GrokLogo} alt="Grok" className="h-8 w-8" />,
  'cohere': <img src={CohereLogo} alt="Cohere" className="h-8 w-8" />,
  'openrouter': <img src={OpenRouterLogo} alt="OpenRouter" className="h-8 w-8" />,
  'groq': <img src={GroqLogo} alt="Groq" className="h-8 w-8" />,
  'zai-global': <img src={ZaiGlobalLogo} alt="Zhipu AI (Global)" className="h-8 w-8" />,
  'zai-cn': <img src={ZaiChinaLogo} alt="Zhipu AI (Chine)" className="h-8 w-8" />,
};