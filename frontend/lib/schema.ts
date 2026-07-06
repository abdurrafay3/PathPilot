import { pgTable, serial, text, integer, timestamp } from "drizzle-orm/pg-core";

export const routeHistoryTable = pgTable("route_history", {
  id: serial("id").primaryKey(),
  prompt: text("prompt").notNull(),
  status: text("status").notNull(),
  duration_minutes: integer("duration_minutes"),
  waypoint_name: text("waypoint_name"),
  created_at: timestamp("created_at").defaultNow().notNull(),
});
