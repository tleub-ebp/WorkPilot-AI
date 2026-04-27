/**
 * Type augmentation: extend ElectronAPI with the Phase35FeaturesAPI methods.
 *
 * The base ElectronAPI is declared in ipc.ts; we use TypeScript interface
 * merging to add the new feature methods without touching that file.
 */

import type { Phase35FeaturesAPI } from "../../preload/api/modules/phase35-features-api";

declare module "./ipc" {
	// eslint-disable-next-line @typescript-eslint/no-empty-interface
	interface ElectronAPI extends Phase35FeaturesAPI {}
}
