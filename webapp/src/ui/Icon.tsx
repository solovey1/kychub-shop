/** Line icons on a 24px grid, drawn like the tab bar: currentColor, 1.7 stroke, round caps. */
export const PATHS = {
  orders: "M5 6h14M5 12h14M5 18h9",
  balance: "M3.5 7.5h17v11h-17zM3.5 7.5l2.5-3h10l2 3M15.5 13h2",
  work: "M4 8.5h16v10H4zM9 8.5v-2h6v2M4 13h16",
  support: "M4 5.5h16v11H9.5L5 20v-3.5H4z",
  admin: "M4 7h9M17 7h3M4 17h3M11 17h9M15 4.5v5M9 14.5v5",
  catalog: "M12 3.5l8 4v9l-8 4-8-4v-9zM4 7.5l8 4 8-4M12 11.5v9",
  people: "M9 11a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM2.5 19.5c0-3.3 2.9-5.5 6.5-5.5s6.5 2.2 6.5 5.5M16 4.8a3.5 3.5 0 010 6.4M18 14.4c2 .7 3.5 2.3 3.5 5.1",
  receipt: "M6 3.5h12v17l-2.4-1.6-1.8 1.6-1.8-1.6-1.8 1.6L8.4 19 6 20.5zM9 8.5h6M9 12.5h6",
  money: "M12 3.5a8.5 8.5 0 100 17 8.5 8.5 0 000-17zM14.5 9.5c-.4-.9-1.3-1.5-2.5-1.5-1.4 0-2.5.7-2.5 1.8 0 2.4 5 1.2 5 3.7 0 1.1-1.1 1.8-2.5 1.8-1.2 0-2.1-.6-2.5-1.5M12 6v2M12 16v2",
  promo: "M3.5 12.5v-8h8l9 9-8 8zM8 8.5h.01",
  broadcasts: "M4 10v4h3l7 4.5v-13L7 10zM18 9.5a4 4 0 010 5",
  stats: "M5 20v-8M12 20V5M19 20v-9",
  settings: "M12 9a3 3 0 100 6 3 3 0 000-6zM12 3.5V6M12 18v2.5M3.5 12H6M18 12h2.5M6 6l1.8 1.8M16.2 16.2L18 18M18 6l-1.8 1.8M7.8 16.2L6 18",
  audit: "M6 3.5h9l3 3v14H6zM9 10h6M9 13.5h6M9 17h3",
} as const;

export const Icon = ({ name }: { name: keyof typeof PATHS }) => (
  <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
    <path d={PATHS[name]} />
  </svg>
);
