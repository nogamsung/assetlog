/**
 * Toss design language — class-string constants.
 * Components import these instead of hard-coding repeated class strings.
 * All classes reference CSS variables via tailwind.config `toss.*` mapping.
 */

export const tossCard =
  'rounded-2xl border border-toss-border bg-toss-card p-5 sm:p-6';

export const tossCardTappable =
  `${tossCard} active:scale-[0.99] transition-transform duration-100 cursor-pointer`;

export const tossButtonPrimary =
  'inline-flex h-12 sm:h-11 w-full sm:w-auto items-center justify-center rounded-xl bg-toss-blue px-5 font-bold text-white transition-all active:scale-[0.98] hover:brightness-95 disabled:opacity-50';

export const tossButtonSecondary =
  'inline-flex h-12 sm:h-11 w-full sm:w-auto items-center justify-center rounded-xl bg-toss-card px-5 font-medium text-toss-text border border-toss-border active:scale-[0.98] hover:bg-toss-border';

export const tossButtonDestructive =
  'inline-flex h-12 sm:h-11 items-center justify-center rounded-xl bg-toss-up/10 px-5 font-bold text-toss-up active:scale-[0.98]';

export const tossInput =
  'h-12 w-full rounded-xl border border-toss-border bg-toss-card px-4 text-base text-toss-textStrong placeholder:text-toss-textDisabled focus:border-toss-blue focus:outline-none focus:ring-2 focus:ring-toss-blue/20';

export const tossLabel =
  'text-sm font-medium text-toss-textWeak mb-2 block';

export const tossPageHeading =
  'text-2xl sm:text-3xl font-bold tracking-tight text-toss-textStrong';

export const tossSectionHeading =
  'text-lg sm:text-xl font-bold text-toss-textStrong';

export const tossHeroNumber =
  'text-4xl sm:text-5xl font-bold tracking-tight tabular-nums text-toss-textStrong';

export const tossCardNumber =
  'text-2xl sm:text-3xl font-bold tracking-tight tabular-nums text-toss-textStrong';
