/**
 * Hook for using Quality Scorer
 */

import { useState, useCallback } from 'react';
import type { QualityScore } from '../../preload/api/modules/quality-api';

export function useQualityScore() {
  const [score, setScore] = useState<QualityScore | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyzeFiles = useCallback(async (files: string[], projectDir?: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await window.electronAPI.quality.analyzeQuality(files, projectDir);
      setScore(result);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to analyze quality';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const analyzePR = useCallback(async (prNumber: number, changedFiles: string[], projectDir?: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await window.electronAPI.quality.analyzePRQuality(prNumber, changedFiles, projectDir);
      setScore(result);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to analyze PR quality';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setScore(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return {
    score,
    isLoading,
    error,
    analyzeFiles,
    analyzePR,
    reset,
  };
}

