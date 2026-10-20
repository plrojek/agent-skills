/* Where the sun stands: NOAA's short solar-position series (good to a fraction of a degree, which
   is far finer than a garden shadow needs). Angles in radians; azimuth clockwise from TRUE north.
   No three.js here on purpose — the maths can be checked on its own. */

const RAD = Math.PI / 180;
const CUM = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];

/** day of the year for the 21st of `month` (1..12): solstices and equinoxes fall on it */
export const dayOfYear = (month, day = 21) => CUM[month - 1] + day;

function terms(doy, hoursUTC) {
  const g = (2 * Math.PI / 365) * (doy - 1 + (hoursUTC - 12) / 24);
  const eqtime = 229.18 * (0.000075 + 0.001868 * Math.cos(g) - 0.032077 * Math.sin(g)
                           - 0.014615 * Math.cos(2 * g) - 0.040849 * Math.sin(2 * g));           // minutes
  const decl = 0.006918 - 0.399912 * Math.cos(g) + 0.070257 * Math.sin(g) - 0.006758 * Math.cos(2 * g)
             + 0.000907 * Math.sin(2 * g) - 0.002697 * Math.cos(3 * g) + 0.00148 * Math.sin(3 * g);
  return { eqtime, decl };
}

/** { az, el } of the sun for a place (degrees, east positive), a day of the year and a UTC hour */
export function sunPosition(latDeg, lonDeg, doy, hoursUTC) {
  const { eqtime, decl } = terms(doy, hoursUTC);
  const lat = latDeg * RAD;
  const tst = hoursUTC * 60 + eqtime + 4 * lonDeg;                 // true solar time, minutes
  const ha = (tst / 4 - 180) * RAD;                                // hour angle, 0 at solar noon
  const sinEl = Math.sin(lat) * Math.sin(decl) + Math.cos(lat) * Math.cos(decl) * Math.cos(ha);
  const el = Math.asin(Math.max(-1, Math.min(1, sinEl)));
  const az = Math.atan2(Math.sin(ha), Math.cos(ha) * Math.sin(lat) - Math.tan(decl) * Math.cos(lat)) + Math.PI;
  return { az, el };
}

/** sunrise and sunset as UTC hours, or null in polar day / night */
export function sunTimes(latDeg, lonDeg, doy) {
  const { eqtime, decl } = terms(doy, 12);
  const lat = latDeg * RAD;
  const c = Math.cos(90.833 * RAD) / (Math.cos(lat) * Math.cos(decl)) - Math.tan(lat) * Math.tan(decl);
  if (c < -1 || c > 1) return null;
  const ha = Math.acos(c) / RAD;
  return { rise: (720 - 4 * (lonDeg + ha) - eqtime) / 60, set: (720 - 4 * (lonDeg - ha) - eqtime) / 60 };
}

/** civil-clock offset from UTC in hours: standard offset, plus one from April to October where DST applies */
export const clockOffset = (site, month) => (site.utc || 0) + (site.dst && month >= 4 && month <= 10 ? 1 : 0);
