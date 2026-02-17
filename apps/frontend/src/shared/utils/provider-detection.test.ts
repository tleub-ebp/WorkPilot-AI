/**
 * Tests for provider detection utilities
 */

import { describe, it, expect } from 'vitest';
import { detectProvider, getProviderLabel, getProviderBadgeColor } from './provider-detection';

describe('provider-detection', () => {
  describe('detectProvider', () => {
    describe('Anthropic provider', () => {
      it('should detect Anthropic from api.anthropic.com', () => {
        const result = detectProvider('https://api.anthropic.com');
        expect(result).toBe('anthropic');
      });

      it('should detect Anthropic with path', () => {
        const result = detectProvider('https://api.anthropic.com/v1/messages');
        expect(result).toBe('anthropic');
      });

      it('should handle subdomain of Anthropic correctly', () => {
        const result = detectProvider('https://sub.api.anthropic.com');
        expect(result).toBe('anthropic');
      });
    });

    describe('OpenAI provider', () => {
      it('should detect OpenAI from api.openai.com', () => {
        const result = detectProvider('https://api.openai.com/v1');
        expect(result).toBe('openai');
      });
    });

    describe('Ollama provider', () => {
      it('should detect Ollama from ollama.ai', () => {
        const result = detectProvider('https://ollama.ai/api');
        expect(result).toBe('ollama');
      });

      it('should detect Ollama from api.ollama.ai', () => {
        const result = detectProvider('https://api.ollama.ai/v1');
        expect(result).toBe('ollama');
      });
    });

    describe('Ollama Local provider', () => {
      it('should detect Ollama Local from localhost', () => {
        const result = detectProvider('http://localhost:11434/v1');
        expect(result).toBe('ollama_local');
      });

      it('should detect Ollama Local from 127.0.0.1', () => {
        const result = detectProvider('http://127.0.0.1:11434/v1');
        expect(result).toBe('ollama_local');
      });
    });

    describe('Unknown provider', () => {
      it('should return unknown for unrecognized domain', () => {
        const result = detectProvider('https://unknown.com/api');
        expect(result).toBe('unknown');
      });

      it('should handle invalid URL gracefully', () => {
        const result = detectProvider('not-a-url');
        expect(result).toBe('unknown');
      });
    });
  });

  describe('getProviderLabel', () => {
    it('should return correct label for Anthropic', () => {
      expect(getProviderLabel('anthropic')).toBe('Anthropic');
    });

    it('should return correct label for OpenAI', () => {
      expect(getProviderLabel('openai')).toBe('OpenAI');
    });

    it('should return correct label for Ollama', () => {
      expect(getProviderLabel('ollama')).toBe('Ollama');
    });

    it('should return correct label for Ollama Local', () => {
      expect(getProviderLabel('ollama_local')).toBe('Ollama (Local)');
    });

    it('should return Unknown for unknown provider', () => {
      expect(getProviderLabel('unknown')).toBe('Unknown');
    });
  });

  describe('getProviderBadgeColor', () => {
    it('should return orange colors for Anthropic', () => {
      const color = getProviderBadgeColor('anthropic');
      expect(color).toContain('orange');
      expect(color).toContain('bg-orange-500/10');
      expect(color).toContain('text-orange-500');
      expect(color).toContain('border-orange-500/20');
    });

    it('should return green colors for OpenAI', () => {
      const color = getProviderBadgeColor('openai');
      expect(color).toContain('green');
      expect(color).toContain('bg-green-500/10');
      expect(color).toContain('text-green-500');
      expect(color).toContain('border-green-500/20');
    });

    it('should return emerald colors for Ollama', () => {
      const color = getProviderBadgeColor('ollama');
      expect(color).toContain('emerald');
      expect(color).toContain('bg-emerald-500/10');
      expect(color).toContain('text-emerald-500');
      expect(color).toContain('border-emerald-500/20');
    });

    it('should return teal colors for Ollama Local', () => {
      const color = getProviderBadgeColor('ollama_local');
      expect(color).toContain('teal');
      expect(color).toContain('bg-teal-500/10');
      expect(color).toContain('text-teal-500');
      expect(color).toContain('border-teal-500/20');
    });

    it('should return gray colors for unknown', () => {
      const color = getProviderBadgeColor('unknown');
      expect(color).toContain('gray');
      expect(color).toContain('bg-gray-500/10');
      expect(color).toContain('text-gray-500');
      expect(color).toContain('border-gray-500/20');
    });
  });
});
