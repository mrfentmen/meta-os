// CB2-409..411 — calendar rules, tested against face/logic.mjs.
//
// The Calendar window imports these functions, so a month boundary the test
// refuses is a month boundary the window cannot render wrongly.
import test from "node:test";
import assert from "node:assert/strict";
import { DOW, daysInMonth, dayKey, monthCells, shiftMonth } from "../face/logic.mjs";

test("CB2-409 month boundaries: Jan 31 to Feb, leap 2028, non-leap 2026", () => {
  // Feb 2028 is a leap month; Feb 2026 is not.
  assert.equal(daysInMonth(2028, 1), 29, "2028-02 has 29 days");
  assert.equal(daysInMonth(2026, 1), 28, "2026-02 has 28 days");

  // Shifting from January never carries a day number across: the view is a
  // month, and the number of days is the new month's own count.
  const jan = { year: 2028, month: 0 };
  const feb = shiftMonth(jan, 1);
  assert.deepEqual(feb, { year: 2028, month: 1 });
  assert.equal(daysInMonth(feb.year, feb.month), 29);

  // Jan 31 + one month is a view shift, not a date addition: it lands on Feb 1,
  // which is why the calendar shifts by month and not by 30 days.
  const jan31 = new Date(2028, 0, 31);
  assert.equal(dayKey(new Date(jan31.getFullYear(), jan31.getMonth() + 1, 1)), "2028-2-1");

  // Every month's day count for one leap and one common year.
  const expected2028 = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  const expected2026 = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  for (let m = 0; m < 12; m++) {
    assert.equal(daysInMonth(2028, m), expected2028[m], "2028-" + (m + 1));
    assert.equal(daysInMonth(2026, m), expected2026[m], "2026-" + (m + 1));
  }
});

test("CB2-410 the first row starts on the documented weekday", () => {
  // A month grid is seven columns starting Sunday, so the number of blank cells
  // before day 1 is the weekday index of the first.
  assert.deepEqual(DOW, ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]);

  // November 2026 starts on a Sunday: no blanks.
  assert.equal(monthCells(2026, 10).leading, 0);
  // February 2026 starts on a Sunday too (checked against the date itself).
  assert.equal(monthCells(2026, 1).leading, new Date(2026, 1, 1).getDay());

  for (const [year, month] of [[2026, 10], [2026, 1], [2028, 1], [2025, 11], [2024, 1]]) {
    const cells = monthCells(year, month);
    assert.equal(cells.leading, new Date(year, month, 1).getDay(), year + "-" + (month + 1) + " leading blanks");
    assert.equal(cells.leading + cells.days.length <= 37, true, "a grid is at most six rows");
    assert.deepEqual(cells.days, Array.from({ length: daysInMonth(year, month) }, (_, i) => i + 1));
  }
});

test("CB2-411 December to January increments the year exactly once", () => {
  const dec = { year: 2026, month: 11 };
  assert.deepEqual(shiftMonth(dec, 1), { year: 2027, month: 0 });
  assert.deepEqual(shiftMonth({ year: 2027, month: 0 }, -1), { year: 2026, month: 11 });

  // A year of forward shifts is exactly twelve steps, no drift.
  let view = { year: 2026, month: 0 };
  for (let i = 0; i < 12; i++) view = shiftMonth(view, 1);
  assert.deepEqual(view, { year: 2027, month: 0 });

  // Multi-year jumps roll once per year, not once per call.
  assert.deepEqual(shiftMonth({ year: 2026, month: 5 }, 18), { year: 2027, month: 11 });
  assert.deepEqual(shiftMonth({ year: 2026, month: 5 }, -18), { year: 2024, month: 11 });

  // The event key the window writes has no zero padding, and the year is the
  // local one — pinning it stops a silent change of key format.
  assert.equal(dayKey(new Date(2026, 0, 5)), "2026-1-5");
  assert.equal(dayKey(new Date(2026, 11, 31)), "2026-12-31");
});
