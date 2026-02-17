import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

// Import English translation resources
import enCommon from './locales/en/common.json';
import enNavigation from './locales/en/navigation.json';
import enSettings from './locales/en/settings.json';
import enTasks from './locales/en/tasks.json';
import enWelcome from './locales/en/welcome.json';
import enOnboarding from './locales/en/onboarding.json';
import enDialogs from './locales/en/dialogs.json';
import enGitlab from './locales/en/gitlab.json';
import enTaskReview from './locales/en/taskReview.json';
import enTerminal from './locales/en/terminal.json';
import enErrors from './locales/en/errors.json';
import enContext from './locales/en/context.json';
import enChangeLog from './locales/en/changelog.json';
import enMigrationWizard from './locales/en/migration-wizard.json';
import enVisualProgramming from './locales/en/visualProgramming.json';
import enInitDialog from './locales/en/initDialog.json';
import enProjectInitModal from './locales/en/projectInitModal.json';

// Import French translation resources
import frCommon from './locales/fr/common.json';
import frNavigation from './locales/fr/navigation.json';
import frSettings from './locales/fr/settings.json';
import frTasks from './locales/fr/tasks.json';
import frWelcome from './locales/fr/welcome.json';
import frOnboarding from './locales/fr/onboarding.json';
import frDialogs from './locales/fr/dialogs.json';
import frGitlab from './locales/fr/gitlab.json';
import frTaskReview from './locales/fr/taskReview.json';
import frTerminal from './locales/fr/terminal.json';
import frErrors from './locales/fr/errors.json';
import frContext from './locales/fr/context.json';
import frChangeLog from './locales/fr/changelog.json';
import frMigrationWizard from './locales/fr/migration-wizard.json';
import frVisualProgramming from './locales/fr/visualProgramming.json';
import frInitDialog from './locales/fr/initDialog.json';
import frProjectInitModal from './locales/fr/projectInitModal.json';

export const defaultNS = 'common';

export const resources = {
  en: {
    common: enCommon,
    navigation: enNavigation,
    settings: enSettings,
    tasks: enTasks,
    welcome: enWelcome,
    onboarding: enOnboarding,
    dialogs: enDialogs,
    initDialog: enInitDialog,
    gitlab: enGitlab,
    taskReview: enTaskReview,
    terminal: enTerminal,
    errors: enErrors,
    context: enContext,
    changelog: enChangeLog,
    migrationWizard: enMigrationWizard,
    visualProgramming: enVisualProgramming,
    projectInitModal: enProjectInitModal
  },
  fr: {
    common: frCommon,
    navigation: frNavigation,
    settings: frSettings,
    tasks: frTasks,
    welcome: frWelcome,
    onboarding: frOnboarding,
    dialogs: frDialogs,
    initDialog: frInitDialog,
    gitlab: frGitlab,
    taskReview: frTaskReview,
    terminal: frTerminal,
    errors: frErrors,
    context: frContext,
    changelog: frChangeLog,
    migrationWizard: frMigrationWizard,
    visualProgramming: frVisualProgramming,
    projectInitModal: frProjectInitModal
  }
} as const;

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: 'en', // Default language (will be overridden by settings)
    fallbackLng: 'en',
    defaultNS,
    ns: [
      'common', 'navigation', 'settings', 'tasks', 'welcome', 'onboarding', 'dialogs', 'initDialog', 'gitlab', 'taskReview', 'terminal', 'errors', 'context', 'changelog', 'migrationWizard', 'visualProgramming', 'projectInitModal'
    ],
    interpolation: {
      escapeValue: false // React already escapes values
    },
    react: {
      useSuspense: false // Disable suspense for Electron compatibility
    }
  });

export default i18n;