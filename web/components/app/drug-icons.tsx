type IconProps = {
  size?: number;
  className?: string;
};

const G = "#10b981";
const GF = "rgba(16,185,129,0.18)";
const GM = "rgba(16,185,129,0.45)";

export function TabletIcon({ size = 48, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <circle cx="24" cy="24" r="14" fill={GF} stroke={G} strokeWidth="2"/>
      <line x1="10" y1="24" x2="38" y2="24" stroke={G} strokeWidth="2" strokeLinecap="round"/>
    </svg>
  );
}

export function CapsuleIcon({ size = 48, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <path d="M 24 18 L 15 18 A 6 6 0 0 0 9 24 A 6 6 0 0 0 15 30 L 24 30 Z" fill={GM}/>
      <rect x="9" y="18" width="30" height="12" rx="6" stroke={G} strokeWidth="2"/>
      <line x1="24" y1="18" x2="24" y2="30" stroke={G} strokeWidth="2"/>
    </svg>
  );
}

export function SyrupIcon({ size = 48, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <rect x="13" y="24" width="22" height="18" rx="4" fill={GF} stroke={G} strokeWidth="2"/>
      <rect x="17" y="14" width="14" height="12" rx="2" fill={GF} stroke={G} strokeWidth="2"/>
      <rect x="15" y="8" width="18" height="8" rx="3" fill={GM} stroke={G} strokeWidth="2"/>
      <line x1="13" y1="33" x2="35" y2="33" stroke={G} strokeWidth="1.5" strokeDasharray="3 2" strokeLinecap="round"/>
    </svg>
  );
}

export function InjectionIcon({ size = 48, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <rect x="10" y="20" width="22" height="8" rx="4" fill={GF} stroke={G} strokeWidth="2"/>
      <rect x="26" y="21.5" width="5" height="5" rx="1" fill={GM}/>
      <line x1="32" y1="24" x2="41" y2="24" stroke={G} strokeWidth="2" strokeLinecap="round"/>
      <line x1="39" y1="20" x2="39" y2="28" stroke={G} strokeWidth="2.5" strokeLinecap="round"/>
      <line x1="5" y1="24" x2="10" y2="24" stroke={G} strokeWidth="1.5" strokeLinecap="round"/>
      <line x1="5" y1="24" x2="8" y2="22" stroke={G} strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  );
}

export function CreamIcon({ size = 48, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <rect x="14" y="16" width="20" height="26" rx="4" fill={GF} stroke={G} strokeWidth="2"/>
      <rect x="17" y="8" width="14" height="10" rx="4" fill={GM} stroke={G} strokeWidth="2"/>
      <line x1="14" y1="38" x2="34" y2="38" stroke={G} strokeWidth="2"/>
      <line x1="16" y1="40.5" x2="32" y2="40.5" stroke={G} strokeWidth="1.5" strokeLinecap="round" opacity="0.5"/>
    </svg>
  );
}

export function DropIcon({ size = 48, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <ellipse cx="24" cy="22" rx="11" ry="13" fill={GF} stroke={G} strokeWidth="2"/>
      <rect x="20" y="33" width="8" height="10" rx="4" fill={GM} stroke={G} strokeWidth="2"/>
      <rect x="19" y="8" width="10" height="7" rx="3" fill={GM} stroke={G} strokeWidth="2"/>
    </svg>
  );
}

export function InhalerIcon({ size = 48, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <rect x="20" y="8" width="14" height="26" rx="6" fill={GF} stroke={G} strokeWidth="2"/>
      <rect x="8" y="28" width="30" height="12" rx="6" fill={GM} stroke={G} strokeWidth="2"/>
      <rect x="23" y="30" width="8" height="8" rx="2" fill={GF}/>
    </svg>
  );
}

export function PowderIcon({ size = 48, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <rect x="8" y="18" width="32" height="18" rx="3" fill={GF} stroke={G} strokeWidth="2"/>
      <line x1="8" y1="18" x2="24" y2="11" stroke={G} strokeWidth="1.5" strokeLinecap="round"/>
      <line x1="40" y1="18" x2="24" y2="11" stroke={G} strokeWidth="1.5" strokeLinecap="round"/>
      <line x1="8" y1="36" x2="24" y2="42" stroke={G} strokeWidth="1.5" strokeLinecap="round"/>
      <line x1="40" y1="36" x2="24" y2="42" stroke={G} strokeWidth="1.5" strokeLinecap="round"/>
      <circle cx="24" cy="27" r="4" fill={GM} stroke={G} strokeWidth="1.5"/>
    </svg>
  );
}

export function SuppositorieIcon({ size = 48, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <path d="M 24 8 C 31 12 36 18 36 26 C 36 34 30 42 24 42 C 18 42 12 34 12 26 C 12 18 17 12 24 8 Z"
        fill={GF} stroke={G} strokeWidth="2" strokeLinejoin="round"/>
      <path d="M 20 22 C 20 19 22 16 24 14" stroke="white" strokeWidth="1.5" strokeLinecap="round" opacity="0.4"/>
    </svg>
  );
}

export function GenericIcon({ size = 48, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <rect x="6" y="13" width="36" height="26" rx="4" fill={GF} stroke={G} strokeWidth="2"/>
      <circle cx="17" cy="23" r="5" fill={GM} stroke={G} strokeWidth="1.5"/>
      <circle cx="31" cy="23" r="5" fill={GM} stroke={G} strokeWidth="1.5"/>
      <circle cx="17" cy="33" r="5" fill={GM} stroke={G} strokeWidth="1.5"/>
      <circle cx="31" cy="33" r="5" fill={GM} stroke={G} strokeWidth="1.5"/>
    </svg>
  );
}

// ── Dashboard feature card icons ─────────────────────────────────────────────

export function AvailabilityIcon({ size = 36, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <rect x="4" y="10" width="20" height="18" rx="4" fill={GF} stroke={G} strokeWidth="1.8"/>
      <circle cx="26" cy="22" r="6" fill={GF} stroke={G} strokeWidth="1.8"/>
      <line x1="30.2" y1="26.2" x2="33" y2="29" stroke={G} strokeWidth="2" strokeLinecap="round"/>
      <line x1="9" y1="16" x2="18" y2="16" stroke={G} strokeWidth="1.5" strokeLinecap="round"/>
      <line x1="9" y1="20" x2="16" y2="20" stroke={G} strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  );
}

export function AskPharmacistIcon({ size = 36, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <path d="M 4 6 H 32 A 2 2 0 0 1 34 8 V 24 A 2 2 0 0 1 32 26 H 12 L 6 32 V 26 H 4 A 2 2 0 0 1 2 24 V 8 A 2 2 0 0 1 4 6 Z"
        fill={GF} stroke={G} strokeWidth="1.8" strokeLinejoin="round"/>
      <line x1="18" y1="11" x2="18" y2="21" stroke={G} strokeWidth="2" strokeLinecap="round"/>
      <line x1="13" y1="16" x2="23" y2="16" stroke={G} strokeWidth="2" strokeLinecap="round"/>
    </svg>
  );
}

export function RequestsListIcon({ size = 36, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <rect x="6" y="4" width="24" height="30" rx="4" fill={GF} stroke={G} strokeWidth="1.8"/>
      <rect x="14" y="1" width="8" height="6" rx="2" fill={GM} stroke={G} strokeWidth="1.5"/>
      <line x1="11" y1="14" x2="25" y2="14" stroke={G} strokeWidth="1.5" strokeLinecap="round"/>
      <line x1="11" y1="19" x2="25" y2="19" stroke={G} strokeWidth="1.5" strokeLinecap="round"/>
      <line x1="11" y1="24" x2="20" y2="24" stroke={G} strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  );
}

export function MedicationsIcon({ size = 36, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <rect x="2" y="9" width="32" height="20" rx="4" fill={GF} stroke={G} strokeWidth="1.8"/>
      <circle cx="11" cy="16" r="4" fill={GM} stroke={G} strokeWidth="1.5"/>
      <circle cx="25" cy="16" r="4" fill={GM} stroke={G} strokeWidth="1.5"/>
      <circle cx="11" cy="24" r="4" fill={GM} stroke={G} strokeWidth="1.5"/>
      <circle cx="25" cy="24" r="4" fill={GM} stroke={G} strokeWidth="1.5"/>
    </svg>
  );
}

export function TelegramIcon({ size = 24, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <path d="M21.5 4.5L2.5 11.5L9.5 13.5L13.5 20.5L16.5 10.5L21.5 4.5Z"
        fill="rgba(0,136,204,0.25)" stroke="#0088cc" strokeWidth="1.5" strokeLinejoin="round"/>
      <path d="M9.5 13.5L13.5 20.5" stroke="#0088cc" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M9.5 13.5L16.5 10.5" stroke="#0088cc" strokeWidth="1" strokeLinecap="round"/>
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
}: {
  form?: string | null;
  size?: number;
  className?: string;
}) {
  const key = (form ? getDrugIconKey(form) : "generic") as IconKey;
  const Icon = ICON_MAP[key] ?? GenericIcon;
  return <Icon size={size} className={className} />;
}
