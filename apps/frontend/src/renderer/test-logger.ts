/**
 * Test simple pour vérifier que le service de logs renderer fonctionne
 */

import { rendererLog } from './services/renderer-logger';

rendererLog.debug('Test message de debug');
rendererLog.info('Test message info');
rendererLog.success('Test message success');
rendererLog.warning('Test message warning');
rendererLog.error('Test message error');

// Test des modules spécifiques
rendererLog.context.debug('Context debug message');
rendererLog.github.info('GitHub info message');
rendererLog.azure.warning('Azure warning message');
