import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const response = NextResponse.json({
    success: true,
    message: "Signed out successfully",
  });

  const isHttps =
    request.url.startsWith("https://") ||
    request.headers.get("x-forwarded-proto") === "https";

  response.cookies.set("session_token", "", {
    httpOnly: true,
    secure: isHttps,
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });

  return response;
}
