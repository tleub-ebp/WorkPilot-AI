/**
 * Toaster Component
 *
 * Renders the toast viewport where toasts are displayed.
 * Should be included once in the app root.
 */

import { useToast } from "../../hooks/use-toast";
import {
	Toast,
	ToastClose,
	ToastDescription,
	ToastProvider,
	ToastTitle,
	ToastViewport,
} from "./toast";

export function Toaster() {
	const { toasts, dismiss } = useToast();

	return (
		<ToastProvider>
			{toasts.map(({ id, title, description, action, onClick, ...props }) => (
				<Toast key={id} {...props}>
					<div
						className={onClick ? "grid gap-1 cursor-pointer" : "grid gap-1"}
						onClick={
							onClick
								? () => {
										onClick();
										dismiss(id);
									}
								: undefined
						}
					>
						{title && <ToastTitle>{title}</ToastTitle>}
						{description && <ToastDescription>{description}</ToastDescription>}
					</div>
					{action && (
						<div className="flex items-center gap-2">
							{action}
							<ToastClose />
						</div>
					)}
					{!action && <ToastClose />}
				</Toast>
			))}
			<ToastViewport />
		</ToastProvider>
	);
}
