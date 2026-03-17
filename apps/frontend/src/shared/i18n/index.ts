import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

// Import English translation resources
import enAppEmulator from './locales/en/appEmulator.json';
import enAnalytics from './locales/en/analytics.json';
import enChangelog from './locales/en/changelog.json';
import enCodePlayground from './locales/en/codePlayground.json';
import enCodeReview from './locales/en/codeReview.json';
import enCollaboration from './locales/en/collaboration.json';
import enCommon from './locales/en/common.json';
import enConflictPredictor from './locales/en/conflictPredictor.json';
import enContext from './locales/en/context.json';
import enContextAwareSnippets from './locales/en/contextAwareSnippets.json';
import enDialogs from './locales/en/dialogs.json';
import enDocumentation from './locales/en/documentation.json';
import enErrors from './locales/en/errors.json';
import enGitlab from './locales/en/gitlab.json';
import enInitDialog from './locales/en/initDialog.json';
import enInsights from './locales/en/insights.json';
import enLearningLoop from './locales/en/learningLoop.json';
import enMultiRepo from './locales/en/multiRepo.json';
import enMigrationWizard from './locales/en/migration-wizard.json';
import enNaturalLanguageGit from './locales/en/naturalLanguageGit.json';
import enNavigation from './locales/en/navigation.json';
import enOnboarding from './locales/en/onboarding.json';
import enPromptOptimizer from './locales/en/promptOptimizer.json';
import enProjectInitModal from './locales/en/projectInitModal.json';
import enReplay from './locales/en/replay.json';
import enRefactoring from './locales/en/refactoring.json';
import enRoadmap from './locales/en/roadmap.json';
import enSettings from './locales/en/settings.json';
import enStreaming from './locales/en/streaming.json';
import enTaskReview from './locales/en/taskReview.json';
import enTasks from './locales/en/tasks.json';
import enTerminal from './locales/en/terminal.json';
import enTestGeneration from './locales/en/testGeneration.json';
import enVisualProgramming from './locales/en/visualProgramming.json';
import enMissionControl from './locales/en/missionControl.json';
import enPixelOffice from './locales/en/pixelOffice.json';
import enSelfHealing from './locales/en/selfHealing.json';
import enWelcome from './locales/en/welcome.json';

// Import French translation resources
import frAppEmulator from './locales/fr/appEmulator.json';
import frAnalytics from './locales/fr/analytics.json';
import frChangelog from './locales/fr/changelog.json';
import frCodePlayground from './locales/fr/codePlayground.json';
import frCodeReview from './locales/fr/codeReview.json';
import frCollaboration from './locales/fr/collaboration.json';
import frCommon from './locales/fr/common.json';
import frConflictPredictor from './locales/fr/conflictPredictor.json';
import frContext from './locales/fr/context.json';
import frContextAwareSnippets from './locales/fr/contextAwareSnippets.json';
import frDialogs from './locales/fr/dialogs.json';
import frDocumentation from './locales/fr/documentation.json';
import frErrors from './locales/fr/errors.json';
import frGitlab from './locales/fr/gitlab.json';
import frInitDialog from './locales/fr/initDialog.json';
import frInsights from './locales/fr/insights.json';
import frLearningLoop from './locales/fr/learningLoop.json';
import frMultiRepo from './locales/fr/multiRepo.json';
import frMigrationWizard from './locales/fr/migration-wizard.json';
import frMissionControl from './locales/fr/missionControl.json';
import frNaturalLanguageGit from './locales/fr/naturalLanguageGit.json';
import frNavigation from './locales/fr/navigation.json';
import frOnboarding from './locales/fr/onboarding.json';
import frPromptOptimizer from './locales/fr/promptOptimizer.json';
import frProjectInitModal from './locales/fr/projectInitModal.json';
import frReplay from './locales/fr/replay.json';
import frRefactoring from './locales/fr/refactoring.json';
import frRoadmap from './locales/fr/roadmap.json';
import frSettings from './locales/fr/settings.json';
import frStreaming from './locales/fr/streaming.json';
import frTaskReview from './locales/fr/taskReview.json';
import frTasks from './locales/fr/tasks.json';
import frTerminal from './locales/fr/terminal.json';
import frTestGeneration from './locales/fr/testGeneration.json';
import frVisualProgramming from './locales/fr/visualProgramming.json';
import frPixelOffice from './locales/fr/pixelOffice.json';
import frSelfHealing from './locales/fr/selfHealing.json';
import frWelcome from './locales/fr/welcome.json';

export const defaultNS = 'common';

export const resources = {
  en: {
    appEmulator: enAppEmulator,
    analytics: enAnalytics,
    changelog: enChangelog,
    codePlayground: enCodePlayground,
    codeReview: enCodeReview,
    collaboration: enCollaboration,
    common: enCommon,
    conflictPredictor: enConflictPredictor,
    context: enContext,
    contextAwareSnippets: enContextAwareSnippets,
    dialogs: enDialogs,
    documentation: enDocumentation,
    errors: enErrors,
    gitlab: enGitlab,
    initDialog: enInitDialog,
    insights: enInsights,
    learningLoop: enLearningLoop,
    multiRepo: enMultiRepo,
    migrationWizard: enMigrationWizard,
    missionControl: enMissionControl,
    pixelOffice: enPixelOffice,
    selfHealing: enSelfHealing,
    naturalLanguageGit: enNaturalLanguageGit,
    navigation: enNavigation,
    onboarding: enOnboarding,
    promptOptimizer: enPromptOptimizer,
    projectInitModal: enProjectInitModal,
    replay: enReplay,
    refactoring: enRefactoring,
    roadmap: enRoadmap,
    settings: enSettings,
    streaming: enStreaming,
    taskReview: enTaskReview,
    tasks: enTasks,
    terminal: enTerminal,
    testGeneration: enTestGeneration,
    visualProgramming: enVisualProgramming,
    welcome: enWelcome
  },
  fr: {
    appEmulator: frAppEmulator,
    analytics: frAnalytics,
    changelog: frChangelog,
    codePlayground: frCodePlayground,
    codeReview: frCodeReview,
    collaboration: frCollaboration,
    common: frCommon,
    conflictPredictor: frConflictPredictor,
    context: frContext,
    contextAwareSnippets: frContextAwareSnippets,
    dialogs: frDialogs,
    documentation: frDocumentation,
    errors: frErrors,
    gitlab: frGitlab,
    initDialog: frInitDialog,
    insights: frInsights,
    learningLoop: frLearningLoop,
    multiRepo: frMultiRepo,
    migrationWizard: frMigrationWizard,
    missionControl: frMissionControl,
    pixelOffice: frPixelOffice,
    selfHealing: frSelfHealing,
    naturalLanguageGit: frNaturalLanguageGit,
    navigation: frNavigation,
    onboarding: frOnboarding,
    promptOptimizer: frPromptOptimizer,
    projectInitModal: frProjectInitModal,
    replay: frReplay,
    refactoring: frRefactoring,
    roadmap: frRoadmap,
    settings: frSettings,
    streaming: frStreaming,
    taskReview: frTaskReview,
    tasks: frTasks,
    terminal: frTerminal,
    testGeneration: frTestGeneration,
    visualProgramming: frVisualProgramming,
    welcome: frWelcome
  }
} as const;

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: 'en', 
    fallbackLng: 'en',
    defaultNS,
    ns: [
      'appEmulator',
      'analytics',
      'changelog',
      'codePlayground',
      'codeReview',
      'collaboration',
      'common',
      'conflictPredictor',
      'context',
      'contextAwareSnippets',
      'dialogs',
      'documentation',
      'errors',
      'gitlab',
      'initDialog',
      'insights',
      'learningLoop',
      'multiRepo',
      'migrationWizard',
      'missionControl',
      'pixelOffice',
      'selfHealing',
      'naturalLanguageGit',
      'navigation',
      'onboarding',
      'promptOptimizer',
      'projectInitModal',
      'replay',
      'refactoring',
      'roadmap',
      'settings',
      'streaming',
      'taskReview',
      'tasks',
      'terminal',
      'testGeneration',
      'visualProgramming',
      'welcome'
    ],
    interpolation: {
      escapeValue: false 
    },
    react: {
      useSuspense: false 
    }
  });

export default i18n;