import type { INullable } from "../types/common";
import { MS_PER_MINUTE, MINUTES_PER_DAY, MINUTES_PER_HOUR } from "../constants/time";

const LOCAL_FORMAT = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

/**
 * @function formatAge
 * @description Renders elapsed minutes as a short relative age.
 */
function formatAge(minutes: number): string {
  if (minutes < 1) return "just now";
  if (minutes < MINUTES_PER_HOUR) return `${minutes}m ago`;
  if (minutes < MINUTES_PER_DAY) return `${Math.floor(minutes / MINUTES_PER_HOUR)}h ago`;
  return `${Math.floor(minutes / MINUTES_PER_DAY)}d ago`;
}

/**
 * @function formatSeenAt
 * @description Turns an ISO UTC stamp into local date, time and age.
 */
export function formatSeenAt(isoUtc: string): string {
  const stamp = new Date(isoUtc);
  if (Number.isNaN(stamp.getTime())) return isoUtc;
  const minutes = Math.max(0, Math.floor((Date.now() - stamp.getTime()) / MS_PER_MINUTE));
  return `${LOCAL_FORMAT.format(stamp)} · ${formatAge(minutes)}`;
}

/**
 * @function formatClosedAt
 * @description Turns the engine's "MM-DD HH:MM UTC" stamp into local time, using the seen year.
 */
export function formatClosedAt({ closedUtc, seenIsoUtc }: { closedUtc: string; seenIsoUtc: string }): string {
  const closed = parseEngineStamp({ stampUtc: closedUtc, seenIsoUtc });
  return closed ? LOCAL_FORMAT.format(closed) : closedUtc;
}

/**
 * @function parseEngineStamp
 * @description Reads an "MM-DD HH:MM UTC" stamp as a date, taking the year from the sighting.
 */
export function parseEngineStamp({ stampUtc, seenIsoUtc }: { stampUtc: string; seenIsoUtc: string }): INullable<Date> {
  const parts = /^(\d{2})-(\d{2}) (\d{2}):(\d{2}) UTC$/.exec(stampUtc);
  const seen = new Date(seenIsoUtc);
  if (!parts || Number.isNaN(seen.getTime())) return null;
  const [, month, day, hour, minute] = parts.map(Number);
  const closed = new Date(Date.UTC(seen.getUTCFullYear(), month - 1, day, hour, minute));
  // A close always follows the sighting, so an earlier month means it rolled into the next year.
  if (month - 1 < seen.getUTCMonth()) closed.setUTCFullYear(seen.getUTCFullYear() + 1);
  return closed;
}
