import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import * as React from "react";
import { cn } from "../../lib/utils";

// Use modal={false} to prevent Radix Dialog from setting aria-hidden / pointer-events:none
// on document.body, which would block Select / Popover portals rendered outside the dialog tree.
// The overlay div in FullScreenDialogOverlay provides the visual backdrop and focus trapping manually.
const FullScreenDialog = (
	props: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Root>,
) => <DialogPrimitive.Root modal={false} {...props} />;

const FullScreenDialogTrigger = DialogPrimitive.Trigger;

const FullScreenDialogPortal = DialogPrimitive.Portal;

const FullScreenDialogClose = DialogPrimitive.Close;

const FullScreenDialogOverlay = React.forwardRef<
	React.ElementRef<typeof DialogPrimitive.Overlay>,
	React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
	<DialogPrimitive.Overlay
		ref={ref}
		className={cn(
			// pointer-events-all ensures clicks on the backdrop don't reach elements behind the dialog.
			// This is necessary because we use modal={false} (to allow Select portals to work inside
			// a Radix Dialog), so the default Radix pointer-events blocking is disabled.
			"fixed inset-0 z-50 bg-background/95 backdrop-blur-sm pointer-events-auto",
			"data-[state=open]:animate-in data-[state=closed]:animate-out",
			"data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
			className,
		)}
		{...props}
	/>
));
FullScreenDialogOverlay.displayName = "FullScreenDialogOverlay";

const FullScreenDialogContent = React.forwardRef<
	React.ElementRef<typeof DialogPrimitive.Content>,
	React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>
>(
	(
		{ className, children, onPointerDownOutside, onInteractOutside, ...props },
		ref,
	) => (
		<FullScreenDialogPortal>
			<FullScreenDialogOverlay />
			<DialogPrimitive.Content
				ref={ref}
				className={cn(
					"fixed inset-4 z-50 flex flex-col",
					"bg-card border border-border rounded-2xl",
					"shadow-2xl overflow-hidden",
					"data-[state=open]:animate-in data-[state=closed]:animate-out",
					"data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
					"data-[state=closed]:zoom-out-98 data-[state=open]:zoom-in-98",
					"duration-200",
					className,
				)}
				// Prevent the dialog from closing when interacting with portaled elements
				// (e.g. Select/Popover dropdowns that render outside the dialog tree via Portal).
				// With modal={false}, Radix Dialog fires onPointerDownOutside for any click
				// outside the dialog content — including clicks on Select option lists in portals.
				onPointerDownOutside={(e) => {
					// Ignore clicks that originated on a Radix portal (data-radix-popper-content-wrapper)
					// or any element with a Radix select/popover context attribute.
					const target = e.target as Element | null;
					if (target?.closest("[data-radix-popper-content-wrapper]")) {
						e.preventDefault();
						return;
					}
					onPointerDownOutside?.(e);
				}}
				onInteractOutside={(e) => {
					const target = e.target as Element | null;
					if (target?.closest("[data-radix-popper-content-wrapper]")) {
						e.preventDefault();
						return;
					}
					onInteractOutside?.(e);
				}}
				{...props}
			>
				{children}
				<DialogPrimitive.Close
					className={cn(
						"absolute right-4 top-4 rounded-lg p-2",
						"text-muted-foreground hover:text-foreground",
						"hover:bg-accent transition-colors",
						"focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background",
						"disabled:pointer-events-none z-10",
					)}
				>
					<X className="h-5 w-5" />
					<span className="sr-only">Close</span>
				</DialogPrimitive.Close>
			</DialogPrimitive.Content>
		</FullScreenDialogPortal>
	),
);
FullScreenDialogContent.displayName = "FullScreenDialogContent";

const FullScreenDialogHeader = ({
	className,
	...props
}: React.HTMLAttributes<HTMLDivElement>) => (
	<div
		className={cn(
			"flex flex-col space-y-1.5 p-6 pb-4 border-b border-border",
			className,
		)}
		{...props}
	/>
);
FullScreenDialogHeader.displayName = "FullScreenDialogHeader";

const FullScreenDialogBody = ({
	className,
	...props
}: React.HTMLAttributes<HTMLDivElement>) => (
	<div className={cn("flex-1 overflow-hidden", className)} {...props} />
);
FullScreenDialogBody.displayName = "FullScreenDialogBody";

const FullScreenDialogFooter = ({
	className,
	...props
}: React.HTMLAttributes<HTMLDivElement>) => (
	<div
		className={cn(
			"flex items-center justify-end gap-3 p-6 pt-4 border-t border-border",
			className,
		)}
		{...props}
	/>
);
FullScreenDialogFooter.displayName = "FullScreenDialogFooter";

const FullScreenDialogTitle = React.forwardRef<
	React.ElementRef<typeof DialogPrimitive.Title>,
	React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(({ className, ...props }, ref) => (
	<DialogPrimitive.Title
		ref={ref}
		className={cn(
			"text-xl font-semibold leading-none tracking-tight text-foreground",
			className,
		)}
		{...props}
	/>
));
FullScreenDialogTitle.displayName = "FullScreenDialogTitle";

const FullScreenDialogDescription = React.forwardRef<
	React.ElementRef<typeof DialogPrimitive.Description>,
	React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, ...props }, ref) => (
	<DialogPrimitive.Description
		ref={ref}
		className={cn("text-sm text-muted-foreground", className)}
		{...props}
	/>
));
FullScreenDialogDescription.displayName = "FullScreenDialogDescription";

export {
	FullScreenDialog,
	FullScreenDialogPortal,
	FullScreenDialogOverlay,
	FullScreenDialogClose,
	FullScreenDialogTrigger,
	FullScreenDialogContent,
	FullScreenDialogHeader,
	FullScreenDialogBody,
	FullScreenDialogFooter,
	FullScreenDialogTitle,
	FullScreenDialogDescription,
};
