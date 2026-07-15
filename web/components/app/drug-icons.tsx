type Tone = "brand" | "muted" | "success" | "warning" | "danger" | "disabled";

type IconProps = {
  size?: number;
  className?: string;
  /**
   * Icons express state through `color`, not through a baked-in hex. The family
   * used to hard-code one green (`const G = "#34d98a"`), so a medicine icon
   * looked identical whether its reminder was active, paused or stopped - the
   * icon could not participate in the interface at all. Every stroke and fill is
   * now `currentColor`, and this prop sets it.
   */
  tone?: Tone;
};

const TONE: Record<Tone, string> = {
  brand: "text-[#34d98a]",
  muted: "text-[#b1bdb0]",
  success: "text-[#34d98a]",
  warning: "text-amber-400",
  danger: "text-red-400",
  disabled: "text-white/25",
};

/**
 * Stroke width that renders to a CONSTANT effective thickness at any size.
 *
 * An SVG stroke scales with the viewBox, so an authored width of 1 in a 36
 * viewBox rendered at 28px painted 1 x (28/36) = 0.78px - under one device pixel,
 * which on a 1x Android screen is grey haze rather than a line. This family
 * authored 5 weights across 3 viewBoxes and rendered at 8 sizes, so effective
 * stroke ranged 0.78-2px, sometimes three weights inside a single icon. lucide
 * (the rest of the app's iconography) renders a single ~1.5-1.67px stroke.
 *
 * Two weights now, both size-independent: PRIMARY for structure, DETAIL for
 * interior lines. Nothing renders below 1.15px.
 */
const PRIMARY_PX = 1.6;
const DETAIL_PX = 1.15;

function sw(size: number, viewBox: number, px: number = PRIMARY_PX): number {
  return Number(((viewBox / size) * px).toFixed(3));
}

function toneClass(tone: Tone = "brand", className?: string): string {
  return [TONE[tone], className].filter(Boolean).join(" ");
}

export function TabletIcon({ size = 48, className, tone }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={toneClass(tone, className)}>
      <circle cx="24" cy="24" r="14" fill="currentColor" fillOpacity={0.18} stroke="currentColor" strokeWidth={sw(size, 48)}/>
      <line x1="10" y1="24" x2="38" y2="24" stroke="currentColor" strokeWidth={sw(size, 48)} strokeLinecap="round"/>
    </svg>
  );
}

export function CapsuleIcon({ size = 48, className, tone }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={toneClass(tone, className)}>
      <path d="M 24 18 L 15 18 A 6 6 0 0 0 9 24 A 6 6 0 0 0 15 30 L 24 30 Z" fill="currentColor" fillOpacity={0.45}/>
      <rect x="9" y="18" width="30" height="12" rx="6" stroke="currentColor" strokeWidth={sw(size, 48)}/>
      <line x1="24" y1="18" x2="24" y2="30" stroke="currentColor" strokeWidth={sw(size, 48)}/>
    </svg>
  );
}

export function SyrupIcon({ size = 48, className, tone }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={toneClass(tone, className)}>
      <rect x="13" y="24" width="22" height="18" rx="4" fill="currentColor" fillOpacity={0.18} stroke="currentColor" strokeWidth={sw(size, 48)}/>
      <rect x="17" y="14" width="14" height="12" rx="2" fill="currentColor" fillOpacity={0.18} stroke="currentColor" strokeWidth={sw(size, 48)}/>
      <rect x="15" y="8" width="18" height="8" rx="3" fill="currentColor" fillOpacity={0.45} stroke="currentColor" strokeWidth={sw(size, 48)}/>
      <line x1="13" y1="33" x2="35" y2="33" stroke="currentColor" strokeWidth={sw(size, 48, DETAIL_PX)} strokeDasharray="3 2" strokeLinecap="round"/>
    </svg>
  );
}

export function InjectionIcon({ size = 48, className, tone }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={toneClass(tone, className)}>
      <rect x="10" y="20" width="22" height="8" rx="4" fill="currentColor" fillOpacity={0.18} stroke="currentColor" strokeWidth={sw(size, 48)}/>
      <rect x="26" y="21.5" width="5" height="5" rx="1" fill="currentColor" fillOpacity={0.45}/>
      <line x1="32" y1="24" x2="41" y2="24" stroke="currentColor" strokeWidth={sw(size, 48)} strokeLinecap="round"/>
      <line x1="39" y1="20" x2="39" y2="28" stroke="currentColor" strokeWidth={sw(size, 48)} strokeLinecap="round"/>
      <line x1="5" y1="24" x2="10" y2="24" stroke="currentColor" strokeWidth={sw(size, 48, DETAIL_PX)} strokeLinecap="round"/>
      <line x1="5" y1="24" x2="8" y2="22" stroke="currentColor" strokeWidth={sw(size, 48, DETAIL_PX)} strokeLinecap="round"/>
    </svg>
  );
}

export function CreamIcon({ size = 48, className, tone }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={toneClass(tone, className)}>
      <rect x="14" y="16" width="20" height="26" rx="4" fill="currentColor" fillOpacity={0.18} stroke="currentColor" strokeWidth={sw(size, 48)}/>
      <rect x="17" y="8" width="14" height="10" rx="4" fill="currentColor" fillOpacity={0.45} stroke="currentColor" strokeWidth={sw(size, 48)}/>
      <line x1="14" y1="38" x2="34" y2="38" stroke="currentColor" strokeWidth={sw(size, 48)}/>
      <line x1="16" y1="40.5" x2="32" y2="40.5" stroke="currentColor" strokeWidth={sw(size, 48, DETAIL_PX)} strokeLinecap="round" opacity="0.5"/>
    </svg>
  );
}

export function DropIcon({ size = 48, className, tone }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={toneClass(tone, className)}>
      <ellipse cx="24" cy="22" rx="11" ry="13" fill="currentColor" fillOpacity={0.18} stroke="currentColor" strokeWidth={sw(size, 48)}/>
      <rect x="20" y="33" width="8" height="10" rx="4" fill="currentColor" fillOpacity={0.45} stroke="currentColor" strokeWidth={sw(size, 48)}/>
      <rect x="19" y="8" width="10" height="7" rx="3" fill="currentColor" fillOpacity={0.45} stroke="currentColor" strokeWidth={sw(size, 48)}/>
    </svg>
  );
}

export function InhalerIcon({ size = 48, className, tone }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={toneClass(tone, className)}>
      <rect x="20" y="8" width="14" height="26" rx="6" fill="currentColor" fillOpacity={0.18} stroke="currentColor" strokeWidth={sw(size, 48)}/>
      <rect x="8" y="28" width="30" height="12" rx="6" fill="currentColor" fillOpacity={0.45} stroke="currentColor" strokeWidth={sw(size, 48)}/>
      <rect x="23" y="30" width="8" height="8" rx="2" fill="currentColor" fillOpacity={0.18}/>
    </svg>
  );
}

export function PowderIcon({ size = 48, className, tone }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={toneClass(tone, className)}>
      <rect x="8" y="18" width="32" height="18" rx="3" fill="currentColor" fillOpacity={0.18} stroke="currentColor" strokeWidth={sw(size, 48)}/>
      <line x1="8" y1="18" x2="24" y2="11" stroke="currentColor" strokeWidth={sw(size, 48, DETAIL_PX)} strokeLinecap="round"/>
      <line x1="40" y1="18" x2="24" y2="11" stroke="currentColor" strokeWidth={sw(size, 48, DETAIL_PX)} strokeLinecap="round"/>
      <line x1="8" y1="36" x2="24" y2="42" stroke="currentColor" strokeWidth={sw(size, 48, DETAIL_PX)} strokeLinecap="round"/>
      <line x1="40" y1="36" x2="24" y2="42" stroke="currentColor" strokeWidth={sw(size, 48, DETAIL_PX)} strokeLinecap="round"/>
      <circle cx="24" cy="27" r="4" fill="currentColor" fillOpacity={0.45} stroke="currentColor" strokeWidth={sw(size, 48, DETAIL_PX)}/>
    </svg>
  );
}

export function SuppositorieIcon({ size = 48, className, tone }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={toneClass(tone, className)}>
      <path d="M 24 8 C 31 12 36 18 36 26 C 36 34 30 42 24 42 C 18 42 12 34 12 26 C 12 18 17 12 24 8 Z"
        fill="currentColor" fillOpacity={0.18} stroke="currentColor" strokeWidth={sw(size, 48)} strokeLinejoin="round"/>
      <path d="M 20 22 C 20 19 22 16 24 14" stroke="white" strokeWidth={sw(size, 48, DETAIL_PX)} strokeLinecap="round" opacity="0.4"/>
    </svg>
  );
}

export function GenericIcon({ size = 48, className, tone }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={toneClass(tone, className)}>
      <rect x="6" y="13" width="36" height="26" rx="4" fill="currentColor" fillOpacity={0.18} stroke="currentColor" strokeWidth={sw(size, 48)}/>
      <circle cx="17" cy="23" r="5" fill="currentColor" fillOpacity={0.45} stroke="currentColor" strokeWidth={sw(size, 48, DETAIL_PX)}/>
      <circle cx="31" cy="23" r="5" fill="currentColor" fillOpacity={0.45} stroke="currentColor" strokeWidth={sw(size, 48, DETAIL_PX)}/>
      <circle cx="17" cy="33" r="5" fill="currentColor" fillOpacity={0.45} stroke="currentColor" strokeWidth={sw(size, 48, DETAIL_PX)}/>
      <circle cx="31" cy="33" r="5" fill="currentColor" fillOpacity={0.45} stroke="currentColor" strokeWidth={sw(size, 48, DETAIL_PX)}/>
    </svg>
  );
}

// ── Dashboard feature card icons ─────────────────────────────────────────────

export function AvailabilityIcon({ size = 36, className, tone }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg" className={toneClass(tone, className)}>
      <rect x="4" y="10" width="20" height="18" rx="4" fill="currentColor" fillOpacity={0.18} stroke="currentColor" strokeWidth={sw(size, 36)}/>
      <circle cx="26" cy="22" r="6" fill="currentColor" fillOpacity={0.18} stroke="currentColor" strokeWidth={sw(size, 36)}/>
      <line x1="30.2" y1="26.2" x2="33" y2="29" stroke="currentColor" strokeWidth={sw(size, 36)} strokeLinecap="round"/>
      <line x1="9" y1="16" x2="18" y2="16" stroke="currentColor" strokeWidth={sw(size, 36, DETAIL_PX)} strokeLinecap="round"/>
      <line x1="9" y1="20" x2="16" y2="20" stroke="currentColor" strokeWidth={sw(size, 36, DETAIL_PX)} strokeLinecap="round"/>
    </svg>
  );
}

export function AskPharmacistIcon({ size = 36, className, tone }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg" className={toneClass(tone, className)}>
      <path d="M 4 6 H 32 A 2 2 0 0 1 34 8 V 24 A 2 2 0 0 1 32 26 H 12 L 6 32 V 26 H 4 A 2 2 0 0 1 2 24 V 8 A 2 2 0 0 1 4 6 Z"
        fill="currentColor" fillOpacity={0.18} stroke="currentColor" strokeWidth={sw(size, 36)} strokeLinejoin="round"/>
      <line x1="18" y1="11" x2="18" y2="21" stroke="currentColor" strokeWidth={sw(size, 36)} strokeLinecap="round"/>
      <line x1="13" y1="16" x2="23" y2="16" stroke="currentColor" strokeWidth={sw(size, 36)} strokeLinecap="round"/>
    </svg>
  );
}

export function RequestsListIcon({ size = 36, className, tone }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg" className={toneClass(tone, className)}>
      <rect x="6" y="4" width="24" height="30" rx="4" fill="currentColor" fillOpacity={0.18} stroke="currentColor" strokeWidth={sw(size, 36)}/>
      <rect x="14" y="1" width="8" height="6" rx="2" fill="currentColor" fillOpacity={0.45} stroke="currentColor" strokeWidth={sw(size, 36, DETAIL_PX)}/>
      <line x1="11" y1="14" x2="25" y2="14" stroke="currentColor" strokeWidth={sw(size, 36, DETAIL_PX)} strokeLinecap="round"/>
      <line x1="11" y1="19" x2="25" y2="19" stroke="currentColor" strokeWidth={sw(size, 36, DETAIL_PX)} strokeLinecap="round"/>
      <line x1="11" y1="24" x2="20" y2="24" stroke="currentColor" strokeWidth={sw(size, 36, DETAIL_PX)} strokeLinecap="round"/>
    </svg>
  );
}

export function MedicationsIcon({ size = 36, className, tone }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg" className={toneClass(tone, className)}>
      <rect x="2" y="9" width="32" height="20" rx="4" fill="currentColor" fillOpacity={0.18} stroke="currentColor" strokeWidth={sw(size, 36)}/>
      <circle cx="11" cy="16" r="4" fill="currentColor" fillOpacity={0.45} stroke="currentColor" strokeWidth={sw(size, 36, DETAIL_PX)}/>
      <circle cx="25" cy="16" r="4" fill="currentColor" fillOpacity={0.45} stroke="currentColor" strokeWidth={sw(size, 36, DETAIL_PX)}/>
      <circle cx="11" cy="24" r="4" fill="currentColor" fillOpacity={0.45} stroke="currentColor" strokeWidth={sw(size, 36, DETAIL_PX)}/>
      <circle cx="25" cy="24" r="4" fill="currentColor" fillOpacity={0.45} stroke="currentColor" strokeWidth={sw(size, 36, DETAIL_PX)}/>
    </svg>
  );
}

export function TelegramIcon({ size = 24, className, tone }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={toneClass(tone, className)}>
      <path d="M21.5 4.5L2.5 11.5L9.5 13.5L13.5 20.5L16.5 10.5L21.5 4.5Z"
        fill="rgba(0,136,204,0.25)" stroke="#0088cc" strokeWidth={sw(size, 24, DETAIL_PX)} strokeLinejoin="round"/>
      <path d="M9.5 13.5L13.5 20.5" stroke="#0088cc" strokeWidth={sw(size, 24, DETAIL_PX)} strokeLinecap="round"/>
      <path d="M9.5 13.5L16.5 10.5" stroke="#0088cc" strokeWidth={sw(size, 24, DETAIL_PX)} strokeLinecap="round"/>
    </svg>
  );
}

export function ShopIcon({ size = 36, className, tone }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg" className={toneClass(tone, className)}>
      <rect x="4" y="14" width="28" height="17" rx="3" fill="currentColor" fillOpacity={0.18} stroke="currentColor" strokeWidth={sw(size, 36, DETAIL_PX)}/>
      <path d="M12 14 C12 14 10 8 18 8 C26 8 24 14 24 14" stroke="currentColor" strokeWidth={sw(size, 36, DETAIL_PX)} strokeLinecap="round"/>
      <line x1="4" y1="20" x2="32" y2="20" stroke="currentColor" strokeWidth={sw(size, 36, DETAIL_PX)} strokeOpacity="0.4"/>
      <rect x="14" y="22" width="8" height="9" rx="1.5" fill="currentColor" fillOpacity={0.45}/>
    </svg>
  );
}

// ── Composite DrugIcon with icon map ─────────────────────────────────────────

import { getDrugIconKey } from "@/lib/drug-icons";

const ICON_MAP = {
  tablet: TabletIcon,
  capsule: CapsuleIcon,
  syrup: SyrupIcon,
  injection: InjectionIcon,
  cream: CreamIcon,
  drop: DropIcon,
  inhaler: InhalerIcon,
  powder: PowderIcon,
  suppository: SuppositorieIcon,
  generic: GenericIcon,
} as const;

type IconKey = keyof typeof ICON_MAP;

export function DrugIcon({
  form,
  size = 48,
  className,
  tone,
}: {
  form?: string | null;
  size?: number;
  className?: string;
  tone?: Tone;
}) {
  const key = (form ? getDrugIconKey(form) : "generic") as IconKey;
  const Icon = ICON_MAP[key] ?? GenericIcon;
  // The leaf icon applies the tone; passing it through means a caller can say
  // <DrugIcon tone="disabled" /> and have the whole family respond.
  return <Icon size={size} className={className} tone={tone} />;
}
