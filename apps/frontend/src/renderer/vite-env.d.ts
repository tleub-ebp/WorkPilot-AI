/// <reference types="vite/client" />

declare interface ImportMetaEnv {
	readonly VITE_BACKEND_URL?: string;
	// Ajoutez ici d'autres variables d'environnement Vite si besoin
}

declare interface ImportMeta {
	readonly env: ImportMetaEnv;
}
