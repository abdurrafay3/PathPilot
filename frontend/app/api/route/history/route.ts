import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { routeHistoryTable } from "@/lib/schema";
import { desc } from "drizzle-orm";

export async function GET() {
  try {
    const history = await db
      .select()
      .from(routeHistoryTable)
      .orderBy(desc(routeHistoryTable.created_at))
      .limit(50);
    return NextResponse.json(history);
  } catch (err) {
    console.error("Failed to fetch route history", err);
    return NextResponse.json(
      { error: "Failed to fetch route history" },
      { status: 500 }
    );
  }
}
