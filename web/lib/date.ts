/**
 * The calendar date as the user's own clock shows it, as YYYY-MM-DD.
 *
 * Deliberately not `new Date().toISOString().slice(0, 10)`, which was used in
 * three places and is the *UTC* date. Nigeria is WAT (UTC+1) with no DST, so
 * every night between 00:00 and 01:00 the UTC date is still yesterday. This
 * string decides which medications a customer is told to take today: during
 * that hour a course starting today would not appear, and a course that ended
 * yesterday would still be listed as due. Unknown or wrong dates are not
 * acceptable for a medication surface.
 *
 * getFullYear/getMonth/getDate read the local clock - the same clock the
 * reminder was created against, since the create form sends the user's real
 * IANA timezone with it. Built by hand rather than via a locale format so the
 * output can't drift with ICU data or a locale's calendar.
 */
export function localDateKey(d: Date = new Date()): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
