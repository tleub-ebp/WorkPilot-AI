import { useTranslation } from "react-i18next";

/**
 * Hook to format a date as a relative time string with i18n support
 */
export function useFormatRelativeTime() {
	const { t } = useTranslation(["common"]);

	return (date: Date): string => {
		const now = new Date();
		const diffMs = now.getTime() - new Date(date).getTime();
		const diffMins = Math.floor(diffMs / 60000);
		const diffHours = Math.floor(diffMins / 60);
		const diffDays = Math.floor(diffHours / 24);

		if (diffMins < 1) return t("common:time.justNow");
		if (diffMins < 60) return t("common:time.minutesAgo", { count: diffMins });
		if (diffHours < 24) return t("common:time.hoursAgo", { count: diffHours });
		if (diffDays < 7) return t("common:time.daysAgo", { count: diffDays });
		return new Date(date).toLocaleDateString();
	};
}
