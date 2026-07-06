import { pgTable, serial, text, integer, timestamp } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const routeHistoryTable = pgTable("route_history", {
  id: serial("id").primaryKey(),
  prompt: text("prompt").notNull(),
  status: text("status").notNull(),
  duration_minutes: integer("duration_minutes"),
  waypoint_name: text("waypoint_name"),
  created_at: timestamp("created_at").defaultNow().notNull(),
});

export const insertRouteHistorySchema = createInsertSchema(routeHistoryTable).omit({ id: true, created_at: true });
export type InsertRouteHistory = z.infer<typeof insertRouteHistorySchema>;
export type RouteHistory = typeof routeHistoryTable.$inferSelect;
